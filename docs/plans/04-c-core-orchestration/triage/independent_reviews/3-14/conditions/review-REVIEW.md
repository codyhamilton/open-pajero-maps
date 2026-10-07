Verdict: PASS_WITH_FOLLOWUPS

# Plan 43 terminal review (review-conditions-light)

- **Reviewer seat:** Claude CLI, clean context (disclosed; Codex is weekly-limited until 2026-10-10 11:50 AEST). I authored none of the plan 43 work.
- **Range:** master `616fe4c..607e5b6` (`d185fb6`, `e9028a9`, `607e5b6`).
- **Sources:** DESIGN.md, IMPLEMENTATION.md, `3-14/conditions/`, `3-17/conditions/`, `parser/tests/test_bg_eo_stress.py`, and the `residuals.tsv` rows. I also used the plan 37, 28 and 39 inputs and the scratch bytes in `output/scratch-43/`.

## What I re-checked (light only)

- **K1 runs.** The committed `k1old_314.json` and `k1head_314.json` are byte-identical to the scratch outputs (`c07550e0…` and `6b382699…`).
  - The `k1old_314.run.json` `cwd` is `/home/codyh/workspace/open-pajero-maps-43-k1old`.
  - Its scratch log's first line is `W 1cf40f820df7…`.
  - It reports completeness 776, background / background_boundary / interior_cover 0 and name_anchor 1.
  - It differs from the HEAD run only in completeness (776 vs 0). So the old rule really ran.
- **R-G8-1-e.** The `pytest_main_checkout.run.json` `cwd` is `/home/codyh/workspace/open-pajero-maps`.
  - The log echoes `git rev-parse --git-dir` = `.git`, the first worktree-list entry, and `d185fb6`.
  - Result: 1458 passed, 10 skipped, 1 xfailed, exit 0.
  - `scratch-3-11/G` is absent in both checkouts, so the skips are not an artefact of the main checkout.
- **R-G8-1-b sha binding.** `historical_bg/protected_after_39.json` pins `output/scratch-14/G_new/ALLDATA.KWI` = `4ed9cd80…`, which is the path that `p1/run_k1.sh` used.
- **P2 bytes.** `sha256sum -c` passes for every line of `p2_bytes.sha256` (run from the main-checkout root) and `k1old_all.sha256` (run from `/home/codyh/workspace`).
  - The fresh K1 `completeness.bin` is `1a91b1c2…`, the same as `dump_raw`.
- **Classify re-run.** I re-ran `k1_triage classify` (current CLI) on `p2/dump_forced` into `/tmp`.
  - Result: 776 / 468 / 308, O01 363 / O04 3 / O05 102, PARTITION FAIL, rc 1.
  - `assign_completeness.u16` is byte-identical to the committed run's.
- **`dump_ext43` contents.**
  - The name_anchor row is (0, 0, 541) with other_mechanism 6. Its `s02_producer_verified` and `residual_crossing_verified` are both 0.
  - Completeness mechanism counts are {0: 308, 4: 363, 5: 102, 7: 3}, and `residual_crossing_verified` is 0 on every row.
- **Stress test alone.** 11 passed, 1 xfailed in 6.9 s.
  - I compiled an instrumented copy of the probe in `/tmp`, with every `return -1` in `_cenc.c` tagged with its line number.
  - It shows that all 5 of the 20k declines (r359, r8475, r11892, r14503, r19650) leave through `_cenc.c:885`, then propagate through `:951`.
- **CLI history.** `ac1a64d` (3-17, 00:45) is an ancestor of `8b6eb55` (10:07, "Classify empty dump kinds as zero-row partitions").
  - `k1_triage.py` and `dump_io.py` were last changed at `f3def00` before `ac1a64d`.
  - Between `ac1a64d` and master the completeness rules are identical, and the O03 rule differs only in its note text.
- **Characterisation script.** `scratch-43/charact.py` is identical to the committed `stress_characterise_20k.py`.

## Findings

### 1. Medium: an unexplained deviation is carried in prose only (R-G8-1-b context)

**Evidence.** `window_before.json` per-window boundary "before" counts disagree with the 3-13 table in `causes_rootcause.md` L60–77:

| Window | 3-13 table | window_before.json |
| --- | ---: | ---: |
| 1 | 255 | 403 |
| 2 | 829 | 1,224 |
| 3 | 90 | 117 (type) / 356 (all types) |
| 4 | 60 | 191 |
| 6 | 132 | 264 |
| 7 | 196 | 452 |
| 8 | 132 | 304 |

IMPLEMENTATION calls this "not reconciled, context only" (Carried 2), but no `residuals.tsv` row names it. Cody's standing rule is "no unexplained deviations — each has a root cause". Close-out will collapse IMPLEMENTATION, and this item can be lost.

The "Fill counts equal the 3-13 table exactly" sentence also picks a different column per window:

- the 0/291 window uses `background_all_types` (69; 62 are type 291);
- the 0/289 window uses `background_type` (32; all types = 64).

**Fix.**
- Open a residual row (for example R-G8-1-b-a, owner Design) that names the count-basis mismatch (HEAD-checker dump rows vs 3-13 counting). Leave the blocking status for Design, or reconcile the counts.
- Restate the fill sentence with a single, named column basis.

The after-0 supersession itself is unaffected.

### 2. Low: the R-G8-1-d-a "root cause" is a locus, and its evidence is not committed

**Evidence.**
- The record says "Root cause located … `_cenc.c:885`", but no committed artefact shows which `return -1` fired. My instrumented run confirms `:885` for all 5 declines, so the locus is right.
- The guard at `:885` is `g_eh[h].used || np >= ne`, and the two arms are not distinguished.
- Why the face walk meets a used half-edge (an angle tie, collinear overlap, …) is not established.
- The claim that "a decline is a build error" holds: `enc_bg` returns -1 at `_cenc.c:1070`, the `_e2.c:48` doc says the build treats a declined row as an error, and `cenc.py` has no fallback. The record does not cite these.
- "No AU input reaches it" is supported only for spool/encoder pairs that have actually been built.
- The `KNOWN_DECLINES` set equality plus `xfail(strict=True)` treatment is sound: a fix trips the suite, and so does a new decline.

**Fix.**
- Reword "root cause located" to "decline site located (`:885`; `used` vs `np >= ne` arm not split)".
- Commit the instrumented trace, or a one-line reproduction.
- Cite `_cenc.c:1070` and `_e2.c:48` for "build error".
- Scope "no AU input reaches it" to the built spools.

The row correctly stays `blocks-phase3`.

### 3. Low: R-G8-2-f "proven per row" overstates, and R-G8-4-a does not cross-reference f-a

**Evidence.**
- `compare.json`'s `delta_equals_plan37_34` and `delta_rule_matches_plan37_prediction` are close to tautological:
  - plan 37 built its 34-row set from the same inputs (plan 28 TSV `43cbc2c0…` ∩ plan 31 cells `77ff1d86…`);
  - every completeness rule is a bare `other_mechanism == code`.
- The only new evidence is that the classify CLI, run on those bytes, gives plan 37's prediction (as expected).
- R-G8-4-a "regenerated" carries the same unverified premise as R-G8-2-f-a: the forced set comes from plan 31's list, not the lost `AU.differing_cells.tsv`. The R-G8-4-a row does not mention f-a.

The split itself is right: the 3-15 review's closing condition says the row "closes only if that file is recovered and hashed", and f-a keeps `blocks-phase3` with Cody as owner and no decision taken.

**Fix.**
- Reword R-G8-2-f to "plan 37's identity re-executed through the classify CLI; consistent".
- Add "premise shared with R-G8-2-f-a" to R-G8-4-a.

### 4. Low: the S2e name_anchor byte is reconstructed, and its committed source is not cited

**Evidence.**
- `build_ext.py` writes `other_mechanism = 6`. O03's only predicate is `other_mechanism == 6`, so "PARTITION OK" follows by construction once the byte is written. The run verifies the CLI and rule semantics, not the 3-17 bytes.
- The original source, `scratch-3-08/side_name_anchor.npy` (`cause_table.md:57`), is gone.
- The byte is still evidenced, not invented:
  - `cause_table.md:24,36` assigns exactly one O03 row at (L0, 0, 541);
  - that cell is not in plan 31's changed list (asserted in `build_ext.py`);
  - `rebaseline_3-17_9064.md:112` says the extension inherited bytes on unchanged cells.
- `build_ext.py` and IMPLEMENTATION cite plan 29 and 3-08 item 7 (row identity), not the classification that fixes the byte value.

Forcing `other_mechanism` to 0 on plan 31's changed cells (34 rows) is a faithful reading of "conservatively zeroes it on changed cells". It is not an invented assignment. `s02_producer_verified` comes through `dump_join` unchanged, and `residual_crossing_verified` is 0 on every row; no completeness rule reads either field.

**Fix.**
- Cite `cause_table.md:36` as the source of byte 6 in `build_ext.py` and IMPLEMENTATION.
- State that S2e verifies CLI behaviour on a byte inferred from the committed pre-3-14 classification.

### 5. Low: K1 run identity and sha-binding details

**Evidence.**
- **`k1head_314` run record.** The committed `k1head_314.run.json` argv has `--out …/k1old_314.json`. It was renamed from the cwd-slip run (scratch `k1head_314_cwdslip.*`).
- **Misleading log line.** That run's log starts `W 1cf40f8…`, which is the throwaway worktree's HEAD, not the cwd's.
- **Unbound HEAD claim.** No artefact captures the HEAD of the cwd checkout for the claimed "master `6a65cf9`". It is only consistent with commit times: `6a65cf9` at 17:34, run file at 17:37, `d185fb6` at 17:45.
- **Hash timing.** The disc was hashed once, after the second run (`k1old_314.disc_sha.txt`), not "right after" the HEAD run as R-G8-1-b says.
- **"Bound in the report".** R-G8-1-c's closing text asks for the "disc sha bound in the report". `quantisation_roundtrip` records only the basename `ALLDATA.KWI`, so the binding is the sidecar `disc_sha_4ed9cd80.txt`. The Design wording tolerates this.

R-G8-1-b does not depend on the HEAD run: plan 39's `k1_314.json` plus `protected_after_39.json`, and `k1old_314` (background family 0), carry it.

**Fix.**
- In the README, note the rename and that the `W` line is the worktree's HEAD.
- Mark `6a65cf9` as inferred from commit times.
- Change "re-hashed right after" to "re-hashed once after both runs (17:42)".

### 6. Low: stress-test coverage is weaker than its labels

**Evidence.**
- **Design minimum met.** Seed 4314, 1,000 checked self-crossing rings, rings extending past the rect, parity / bounds / record count, a room−1 → −2 check with a byte-identical retry, and 10 explicit cases.
- **eo_connect.** `eo_connect` runs on every `eo_clip`. Nothing asserts that its connection branch (`v >= 0`) is reached. `island_hole_island` relies on its collinear connector edges cancelling by parity to produce separate components.
- **Termination.** Termination is one 600 s timeout per child batch. A hang fails the test but does not identify the ring.
- **Unguarded loop.** `eo_connect` is `for(;;)` with no iteration bound. The review asked for a "guarded eo_connect" termination case; what the test provides is an external timeout, not a guard.

**Fix.**
- Optionally assert that the connection branch is reached (a probe counter), or document the parity-cancellation construction in the test.
- Record that the "guard" is the child timeout.

### 7. Low: record and provenance hygiene

**Evidence.**
- **`docs/provenance.md` scratch-43 section.**
  - It omits `probe.so`, `charact.py` (identical to the committed script), `res_p1.py`, `tmp/` and `output/tmp-agent`.
  - It says "nothing else reads it", but the committed `forced_zero.py`, `build_ext.py` and `compare.py` hard-code `output/scratch-43` paths.
- **Sha file roots.** The two sha files use different, undocumented roots: the main checkout for `p2_bytes.sha256`, and `/home/codyh/workspace` for `k1old_all.sha256`.
- **Exit-2 runs.** The four `run_p2.sh` steps that exited 2 (missing extension columns) are recorded in the README but not in the IMPLEMENTATION Phase 2 deviations.
- **Clean-checkout claim.** R-G8-1-e's "clean before and after" has no committed `git status` capture.
- **Log naming.** One killed log is named `…killed_by_host_shutdown_1753`, while the record says "reboot".

**Fix.**
- Complete the provenance list and drop "nothing else reads it".
- Document each sha file's root.
- Add the exit-2 runs to the P2 deviations.

### 8. Info: S2a reading is correct

"Unchanged CLI" in 3-17 means the CLI as it stood at 3-17.

- `ac1a64d` is 3-17's commit, and `8b6eb55` (the zero-row rejection removal) came after it.
- The reproduced stderr is `ValueError …background.bin: zero-row kinds are unsupported (as in the baseline)`, rc 1, raised from `dump_io.py:82`.
- Recording the current CLI result alongside it (whole-dump partition, PARTITION FAIL) is appropriate.

### 9. Info: governance checks pass

- **Status changes.** Every changed row is either discharged with committed evidence or newly opened as `blocks-phase3`: R-G8-1-d-a (owner "unowned → Design") and R-G8-2-f-a (owner "Cody (via Design)", listed, not decided).
- **No waivers or new rulings.** Nothing is waived, and no new decision is attributed to Cody or Design. "Ruling 5" appears only in the Design (Design's citation, outside this plan's scope).
- **No Phase 3 claim.**
- **Scope.** R-G8-1-f, R-G8-1-g and R-G8-4-c are untouched, as the Design requires.

## Summary

Every row's end state follows from the committed evidence:

- **R-G8-1-c** really used K1 at `1cf40f8`, and its run JSON `cwd` is the worktree.
- **R-G8-1-e** really ran in the main checkout.
- **R-G8-1-b**'s supersession is honest.
- **The P2 regeneration** reproduces the 3-17 counts byte-for-byte on pinned inputs.

Follow-ups are record fixes, plus one missing residual row (finding 1). Nothing should be un-discharged.
