# Implementation — 14 completeness root cause

- Tool: Phase 1 Codex `gpt-6.1-sol`; Phase 2 units 2-01 OpenCode DeepSeek Flash, 2-02/2-03/close Execute background worker (CHM reseated the assigned instance to Codex at 01:35 for any new seats)
- Session: Phase 2 refine + execute
- Started: 2026-10-05 ~23:05 Australia/Brisbane (Phase 1)
- Phase 1 closed: 2026-10-05 ~23:34 Australia/Brisbane
- Phase 2 refine: 2026-10-06 ~00:09 Australia/Brisbane
- Phase 2 closed: 2026-10-06 02:09 Australia/Brisbane (`8c37bae`)
- Phase 3: orchestrator Execute background worker; unit workers Codex `gpt-6.1-sol` (high) via `codex exec`, one at a time; refine 2026-10-06 ~02:15 Australia/Brisbane
- Phase 3 closed: 2026-10-06 ~03:45 Australia/Brisbane (trailer commit `Workflow-Phase: 14-completeness-root-cause:3`)

## Phase 1 — Per-row completeness evidence table

**Closed.**

### Disc restore (Execute)

- No local file matched sha `4ed9cd80…` at start (scratch-3-11/G_new remains protected `013586b5…`; `output/ALLDATA.KWI` was `51c254ac…`).
- Fresh full-AU encode under `flock output/.heavy.lock` from main checkout:
  - spool `output/extract_timing/spool` → `output/scratch-14/G_new/ALLDATA.KWI`, `-j4`
  - log `output/scratch-14/full_build.log` (encode 119.0s, assemble 13.5s)
- Result sha256 `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72` — **matched** prior oracle; size 1,692,105,152. No new oracle.
- Protected `output/scratch-3-11/G_new/ALLDATA.KWI` unchanged.

### Evidence (Codex `gpt-6.1-sol`, pid ~2108761, worktree `open-pajero-maps-14-completeness`)

- Brief: `briefs/1-01-evidence-table.md`
- Fresh K1 completeness-only dump under flock, `-j6`: **776** failing identities (drift vs 3-17 failing: **0**).
- Committed table: `triage/completeness_evidence.tsv` (776 rows) + `triage/completeness_evidence.md`
- Flags: all **188** historic and **89** added present and disjoint; **499** in neither.
- Classify: exit 2 — missing `other_mechanism` (sides cleaned). Assignment column = `evidence-gap:other_mechanism` for all 776. Header states verified attributed-by-rule **0** in this table; historical 3-17 partition (468/308) and 3-15 (274) retained as inputs, not substituted. Numeric difference of unresolved evidence entries vs 3-17 unclassified: **+468**; vs 3-15: **+502** (measures missing assignment evidence, not partition movement).
- R/G/spool witnesses under `output/scratch-14/witnesses/` (git-ignored); audit PASS (1,791 byte ranges). One spool source-evidence gap (native row 335).
- Provenance scratch entry for `output/scratch-14/` committed.
- No rule/encoder/checker edits; 3-16/3-17/170 untouched. Plan 04 Phase 3 not claimed closed.

### Carried

- Live O01/O04/O05/O06 partition blocked until `other_mechanism` sides are recovered or recomputed reproducibly (Phase 2 refine rejected blocking on recovery; may try as optional discriminator only).
- One spool source-evidence gap at `(0,1379,1138,288,…)` — which source/requirement branch establishes the K1 demand?
- Assignment-gap numeric deltas (+468 / +502) are not live unattributed drift; do not treat them as count movement in Phase 2.
- Phase 1 R presence is frame-presence (sparse-tile alias possible); Phase 2 unit 2-01 must apply cell-local geometric meet before closing `g-omits-cell-local-dvd-type`.

## Phase 2 — Root-cause groups

**Closed.** Exhaustive, disjoint union map `triage/phase2_membership.tsv` (776):

| Unit | Commit | Group / ledger | Rows | Reproducer |
| --- | --- | --- | ---: | --- |
| 2-01 | `b775e9b` | `g-omits-cell-local-dvd-type` | 342 | `triage/cell_local_2-01.py` |
| 2-02 | `bcb266b` | `r-absent-complete-repair-zero` | 432 | `triage/complete_repair_2-02.py` (EO faces + densified `emit_piece` mirror + production C `bg_shape` probe; 0 emits / 0 C records on 432/432) |
| 2-03 | `e24b89b` | open questions `Q-source-335`, `Q-tile-alias` (765) | 2 | `triage/residuals_2-03.py` |

Predicted Phase 3 movement: up to −342 (2-01, build or checker; Phase 3 picks) and
−432 (2-02, proven non-deviation or checker stops the demand). The 2 open questions
stay open. Production C confirms 2-01 sources give 0 records on 342/342 (densify
caveat closed). Plan heavy guards were used throughout: `run_heavy_python.py`
(flock + memory.peak logs in `output/scratch-14/runs/`), windowed/`--max-seeds`
probes before `--all-seeds`.

**Spool incident (2-02 setup, 00:44).** The live `output/extract_timing/spool` was
destroyed by a symlink step that resolved through the worktree's `output` link.

- Restored with extractor tree `34a04cc`. A tip-extractor rebuild was rejected
  because 138/775 witness cells differed.
- Proofs: 775/775 witness pins match, and a full-AU `-j4` re-encode at `f385ef5`
  gives `4ed9cd80…` (byte-identical).
- Record: `output/scratch-14/spool_recovery/INCIDENT.md` and `docs/provenance.md`.

### Carried to Phase 3

- **Q-source-335.** No spool source reproduces the K1 demand within ±32 cells.
  Instrument the checker read-only to name the demanding shape.
- **Q-tile-alias (765).** The evidence matches the 2-02 mechanism. Design should
  rule whether cell-local R absence counts as `R_polygon_count == 0`.
- **Locus choice.** Phase 3 decides the 2-01 locus (build vs checker) and the 2-02
  disposition (non-deviation vs checker).
- Plan 04 Phase 3 is **not** closed by this plan.

### Phase 2 refine (record)

**Refine accepted (docs-only, Execute).** Approach C: R-presence primary + cell-local check; complete-repair package for R=0; residuals → open questions. Units `2-01`, `2-02`, `2-03` briefed under `briefs/`. `artifact_feedback` MCP unreachable — continued without workflow post.

Seed cross-tab from Phase 1 TSV (pre cell-local / pre repair):

| Bucket | R>0 G=0 | R=0 G=0 |
| --- | ---: | ---: |
| historic_188 | 1 | 187 |
| added_89 | 0 | 89 |
| neither_499 | 342 | 157 |
| **total** | **343** | **433** (incl. row 335 source gap) |

## Phase 3 — Fix or proven non-deviation per group

Refine: **Proceed.** Units 3-01 (demand attribution / 335), 3-02 (765 R zero contribution, Design ruling), 3-03 (checker representable demand for 2-01 + 2-02). See DESIGN "Phase 3 refine". `artifact_feedback` skipped (workflow service barred by the user). Accounting held at `776 = 342 + 432 + 335 + 765` until 3-02 closes.

### 3-01 — demand attribution (Codex `gpt-6.1-sol` high, session `01a10cda-05de-7b50-90f8-971b7946cef7`, `631f97a`)

- **Q-source-335 named.** Demander: `tall=39083:L0:home(1379,1143):ordinal=0`, type 288, branch (c). It is a 4-coordinate triangular sliver.
  - At the cell centre's scan line, its interval is 0.00067 raw wide and misses the centre by 0.348 raw. `Region.inside`'s `TOL=0.5` accepts it.
  - 2-03's ±32 search missed it because that search used strict EO; the home is only 5 rows away.
  - Mirror and production C: 0 records, so it is unrepresentable.
- Status `done with concerns`: the 25-key timing projected 601.5 s, which is ≥10 min, so the run split at kickoff (3-01b).
- Surfaces: `triage/demand_attribution_3-01.{py,tsv,md}`, `reports/3-01-demand-attribution.md`.
- Deviation: rubric read from the installed workflow plugin (the repository path is absent).

### 3-01b — attribution remainder (orchestrator, direct; `5253301` brief, `06a5c1f`)

- 750 keys in two windows (128.8 s and 81.7 s): **776/776 keys, 799 demanders, branches a 1 / b 797 / c 1, all unrepresentable**. 0 errors, 0 C/Python disagreements, 0 mirror/C disagreements, 0 representable exceptions.
- 3-03 prediction: failing 776 → 0, `checked` unchanged.
- Known problem: the script exits 1 on long `--keys` lists (summary filename too long) after `publish`; outputs are complete. Recorded in the 3-01b report.

### 3-02 — dump_row 765 R zero contribution (Codex `gpt-6.1-sol` high; first session `01a10ceb-…` died on a network disconnect before any tracked write; fresh session `01a10cee-2f7c-7b91-bf12-f96338273b86`, `85d80f1`)

- **Proven.** The single R 291 polygon (mult 1, 291 coords) has bbox x `[5341184, 5343857]`, wholly in column 1304. Cell (1307,1756) starts at x `5353472`, a 9,615-raw gap.
  - Clip is empty; mirror emits 0; production C gives 0 records; R emitted-output presence in the cell is false.
  - Positive control emits 1 record.
- **Design ruling, proven branch applied:**
  - 2-02 is amended to "R polygons contributing 0 cell-local records" (`triage/phase3_groups.md`, proof `output/scratch-14/r_contribution/765.json`).
  - 765 is folded into 2-02.
  - The 432 were re-checked from actual R slot decodes: 432/432 have 0 polygons and 0 contribution.
- Accounting is now **776 = 342 (2-01) + 433 (2-02 amended) + 1 (Q-source-335)** (`triage/phase3_membership.tsv`, exhaustive and disjoint).
- Surfaces: `triage/r_contribution_3-02.{py,tsv}`, `triage/phase3_{groups.md,membership.tsv}`, `reports/3-02-765-r-zero-contribution.md`.
- Deviation: rubric read from the installed plugin. Protected shas unchanged.


### 3-03 — checker-representable-demand: over budget

Research only; no implementation or regression added. Required reading and multiplier investigation consumed 15 files including the brief (14 excluding it), crossing the 14-file budget. Stopped as directed. Both protected disc SHAs match the brief. Demand attribution predicts all 776 keys removed and no exceptions. C `k1_shapes` and Python `Shapes` lack per-shape multiplier carriage; tall-shape C ABI needs an owned-path solution, such as recovering spool attributes by existing home/ordinal identity. Independent C/Python EO representability, regression before/after, live K1, identity diff, and fresh re-encode remain undone. Full handoff: `reports/3-03-checker-representable-demand.md`. Existing-suite validation will be recorded in that report before any commit.

Validation: all four existing suites passed, 259 tests in 22.39s, via the heavy runner (child exit 0). No expectation edits. Budget-fallback handoff eligible for commit; implementation remains unfinished.

### 3-03 — checker representable demand (Codex `gpt-6.1-sol`)

- **First attempt** (high, session `01a10cf6-e9b8-7803-90d2-f4d213c2b993`, `9eed7c8`): over budget. A 14-file read cap was hit during required reading, so no code changed; its handoff was kept.
- **Brief amended twice** (`3d71786`, `77f67eb`):
  - own `cenc.py` K1 ABI for multiplier carriage;
  - budget resized;
  - the worker runs in a Codex `workspace-write` sandbox and leaves its changes in the tree, because Auto-review blocked the sandbox-bypass flag and the sandbox has no systemd user scope or git-metadata writes. The orchestrator runs the heavy verification and commits.
- **Retry** (xhigh, session `01a10cfb-e727-7163-90bb-2ee1c5494ed2`): `done with concerns`, the concern being only the sandbox-blocked systemd test.
  - Built: independent C (`_k1_cmp.c`) and Python (`parser/tools/k1_representable.py`) representability filters, with no `_cenc.c` calls. Per-shape multiplier carried through local and tall shapes (`_k1.c`, `_k1.h`, `cenc.py`, `quantisation_roundtrip.py`).
  - 15 new tests (`test_k1_completeness_representable.py` + fixtures): 6 failed before the change, all pass after. Positive controls still fail as intended. No existing expectation was edited.
  - Contradiction reported: the brief's 2-02 count was 432, but it is 433 after 3-02. Brief amended.
- **Orchestrator verification (plan-25 guards, one heavy job at a time):**
  - Tests: 274 passed, including the memory-guard test outside the sandbox (`runs/p3_tests.json`).
  - Live K1 `-j6` on `4ed9cd80…` (`runs/k1_p3.json`, `p3/k1_p3.{json,log}`, 81.4 s, memory.peak 4.0 GiB): **completeness checked 1,800,514 → 1,800,514, failing 776 → 0.** The completeness dump is empty, so all 776 Phase 1 keys left, no new key appeared, and there were no exceptions, matching 3-01's prediction exactly. Every other kind's checked/failing is identical to Phase 1 `k1_full.json` (name_anchor 1 is pre-existing and outside plan 14, so K1 still exits 1).
  - Re-encode `-j4` with the rebuilt `_cenc.so` (`runs/p3_reencode.json`): sha256 `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72`, so the build sha is unchanged.
  - Protected discs unchanged (`013586b5…`, `4ed9cd80…`).

### Phase 3 verification (orchestrator)

**Closed.** Verified on the disc in force through the outcome's own entry point: live K1 (`quantisation_roundtrip.py --engine c -j 6`) on `output/scratch-14/G_new/ALLDATA.KWI` (`4ed9cd80…`) against the restored spool.

| Group (Phase 3 membership) | Rows | Disposition | Root-cause proof |
| --- | ---: | --- | --- |
| 2-01 `g-omits-cell-local-dvd-type` | 342 | (1) checker (3-03 `a890662`) | Phase 2: every member's demanding source gives 0 production-C records in the cell (342/342). 3-01: all demanders enumerated, all unrepresentable |
| 2-02 `r-absent-complete-repair-zero`, amended to "R polygons contributing 0 cell-local records" | 433 (432 + 765) | (1) checker (3-03), with R/G-absent evidence | Phase 2 complete repair: 0 records on 432/432. 3-02 `85d80f1`: R 291 polygon for 765 lies wholly in column 1304 (bbox x 5341184–5343857 against cell x ≥ 5353472), clip empty, mirror 0, C 0, no R emitted piece; 432/432 re-checked from R decodes. 3-01: unrepresentable demanders |
| Q-source-335 (open question) | 1 | No group disposition (Design) | 3-01: tall triangular sliver `tall=39083:L0:home(1379,1143):ordinal=0` misses the cell centre by 0.348 raw. `Region.inside`'s `TOL=0.5` creates the branch-(c) demand; mirror and production C give 0 records |

Counts:
- **Live completeness:** checked 1,800,514 → 1,800,514; failing **776 → 0**. The removal set equals 3-01's prediction exactly (776 keys, 0 exceptions).
- **Live unattributed:** 0.
- **Ledger:** 776 = 342 + 433 + 1 (`triage/phase3_membership.tsv`).
- **Other K1 kinds:** identical to Phase 1 (name_anchor 1 is pre-existing and outside plan 14; K1 still exits 1).
- **Build sha unchanged:** re-encode `4ed9cd80…`.
- O01–O06 and `rules_*.json` untouched. No tolerance was loosened.

**Independent check of 3-03** (orchestrator, after the worker; Cody's rule that no deviation is relabelled away):

1. *Criterion rests on the Phase 2/3 proofs.* Every one of the 776 keys belongs to 2-01, amended 2-02, or Q-source-335 (`phase3_membership.tsv`). Each key's full demander set (799 shapes, from the checker's own `Region`) has 0 production-encoder records (3-01). The live removal set equals that prediction exactly.
   - 3-03's test is independent of the encoder: a port of the Phase 2 mirror, with no `_cenc.c` calls.
   - Demand branches and `checked` are unchanged; only absent pairs with no representable demander pass.
2. *Synthetic positive controls* (`test_k1_completeness_representable.py`, C == Python):
   - G missing a representable square, a surviving 2.4-raw sliver, a bowtie with one representable lobe, or a mult-2 ring that survives densify → **K1 fails**.
   - A second representable demander keeps a TOL-only pair failing.
   - 274 tests pass, including the plan-25 memory-guard test.
3. *Real-data positive control.* `output/scratch-3-11/G_new` (`013586b5…`) was built from the same spool before 3-14's builder fix. Results:
   - Old checker (`0b19b5e`, throwaway worktree, since removed): 739 failing.
   - New checker: **52 failing**.
   - The 52 equal **exactly** the keys that failed on 3-11 but not on the current disc, i.e. the genuine missing footprints that the later build fix repaired. F ⊆ B and B ⊆ F; B ∩ the 776 = ∅.
   - Conclusion: the new checker still catches every real missing representable footprint on real data, and it excuses only the demand that persisted unrepresentable into the current disc.
   - Evidence: `output/scratch-14/p3/indep/{old,new}_k1_311.{json,log}`, dumps, `sets.json`; wrapper logs `runs/indep_{old,new}_k1_311.json`.

Plan 04 Phase 3 is **not** closed by this plan.

### Carried

1. **Design ruling needed: dump_row 335.**
   - DESIGN's 2-02 membership explicitly excluded 335 for lack of a source witness.
   - 3-01 now supplies it, with the 2-02 mechanism: R has 289 only (`R_polygon_count == 0`), G lacks 288, and the demander is unrepresentable.
   - The row no longer fails live. Folding it (342 + 434) needs a ruling like the one 765 got.
2. **Design observation (no scope added):** R emits 288 in the 342 2-01 cells, while the spool holds no representable 288 source there. This is a source-data parity difference, not a K1 completeness defect.
3. **Tooling bug:** `triage/demand_attribution_3-01.py` exits 1 after `publish` on long `--keys` lists (the summary filename is built from the key list). Outputs are complete.
4. **Harness note:** Codex `exec` with the sandbox-bypass flag was blocked by Auto-review at the 3-03 retry. The `workspace-write` sandbox has no systemd user scope (the plan-25 wrapper fails closed) and no git-metadata writes, so sandboxed workers leave their tree and the orchestrator verifies heavily and commits.
5. Plan 04 Phase 3 remains open: name_anchor 1, 3-90 blockers.

`artifact_feedback` skipped for the Phase 3 briefs and reports: the workflow service is barred for this run.

## Terminal review

- Independent review: clean Codex `gpt-6.1-sol` (high), session `01a10d23-a8b2-74d2-a4c9-f95e4e2a8f54`. **REMEDIATE**: F1 high (EO topology), F2 medium (335 disposition). F4 and F5 were fixed in review. F3 and F6 are follow-ups.
- Spot checks 1 (memory guard outside the sandbox) and 2 (disc rehash) pass.
- F1 remediated by a clean Codex agent and verified by the orchestrator. Live failing is still 0, and the older-disc control still detects exactly the 52 genuine build defects. See REVIEW.md's resolution record.
- **Close-out not run.** F2 stands and requires a Design ruling on dump_row 335.

## Design ruling on dump_row 335 (2026-10-06)

- **335 folded into amended 2-02.** Evidence: R has 0 cell-local 288 in the key cell (1379,1138), whose tile carries only 289; G lacks 288; the production encoder gives 0 records.
- **Distinct sub-cause:** a type-288 tall triangular sliver (home (1379,1143)) misses the cell centre by 0.348 raw. The pre-3-03 checker's 0.5-raw centre slack wrongly counted it. Fix: 3-03 (`a890662`) plus remediation-01 (`0dc5cac`).
- **Final accounting: 776 = 342 (2-01) + 434 (2-02), 0 open.** Resolves review F2 (`triage/phase3_membership.tsv`, `triage/phase3_groups.md`).
- **2-01 source-data parity:** recorded as a **proven deviation cause**, not a non-deviation. In the 342 cells R emits 288, while the spool holds no encodable 288 source. G cannot match R without inventing geometry; the cause lies in the source data.
- **Phase 1 is partial:** the per-rule classify assignments were never recovered (review F3). No claim is made beyond that. Design is drafting a follow-up.
- K1 name_anchor 1: outside plan 14; Design is drafting a separate design.
