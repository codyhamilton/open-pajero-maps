# Implementation — 29 K1 name_anchor failure

- Tool: orchestrator is the Execute background worker. Unit workers are Codex `gpt-6.1-sol` (reasoning high) via `codex exec -s workspace-write`, one at a time. Sandboxed workers leave changes in the tree; Execute runs heavy steps under `parser/tools/run_heavy_python.py` and makes the commits.
- Session: plan 29 Execute (Phases 1–2, terminal review, close-out), run after plan 28 per CHM ordering, with no two heavy jobs at once.
- Started: 2026-10-06 ~04:22 Australia/Brisbane (brief authored while plan 28's worker ran).
- Worktree: `/home/codyh/workspace/open-pajero-maps-14-completeness` (detached, pushes fast-forward to `master`); DESIGN landed at `e6436a2`.
- Scratch: `output/scratch-29/` (run logs under `output/scratch-29/runs/`).
- Protected, byte-untouched throughout:
  - `output/scratch-14/G_new/ALLDATA.KWI` (`4ed9cd80…`);
  - `output/scratch-3-11/G_new/ALLDATA.KWI` (`013586b5…`);
  - `output/extract_timing/spool`;
  - the R disc `/run/media/codyh/464210-8480/ALLDATA.KWI` (`8c2d2027…`, read-only mount).

## Phase 1 — The single name_anchor failure is byte-identified against G, spool and R

Refine skipped (DESIGN). One unit, with its brief authored inline: `briefs/1-01-witnesses-verdict.md`.

### 1-01 — G / spool / R byte witnesses and A/B verdict

- **Worker:** Codex `gpt-6.1-sol` (high), sandboxed, 04:22–04:33. 134,618 tokens; the harness reports no turn count. Report: `reports/1-01-witnesses-verdict.md`. Status: `done with concerns` (live runs pending Execute, by design).
- **Built:**
  - `witness_p1.py`: argparse subcommands `g-witness`, `spool-witness`, `r-witness`, `spool-scan`, `verdict`. A bare invocation prints usage and exits 2.
  - Generated `witnesses/*.json`, `witnesses/scan_rejects.tsv` and `phase1_witness.md`.
- **Runs (Execute, guarded, `output/scratch-29/run_p1.{sh,log}`, 04:39):**
  - g/spool/r witnesses exited 0;
  - spool-scan exited 0 (23 s, peak 36 MB);
  - verdict exited **2** with drift: "spool identity differs from Decision 4/G string".
- **Drift diagnosed (Execute):** not a premise drift. The cell, record 0, type 288, string_type 6, lon `77.51903576666666` and transcoded string bytes all match. What differs is that the spool stores the unquantised source latitude `-38.727285888405795`, while DESIGN's table quotes G's decoded latitude `-38.727284749` as the "spool lat". Both lie in the same L0 raw row (G global raw y 2,216,306). The script compared latitude by float equality.
- **Execute fix (small, direct, no worker running):** spool identity and the scan's expected-O03 flag now compare latitude by shared raw row (`|gy(lat) − 2216306| ≤ 0.5`). Re-run `run_p1b.sh`: spool-witness 0, spool-scan 0, verdict 0, with no drift and no concerns. **Verdict A.**
- **Added R reader positive control (Execute):** `r_reader_control.py` → `witnesses/r_reader_control.json`, guarded.
  - Perth L0 (827,866) resolves on both R (4 frames, 739 names) and G (4 frames, 3,879 names), so the reader works.
  - Census of the 32×64-cell block holding (0,541): R has **0** frames. G has frames at (0,541) (1 name, the O03 item) plus (0,562) and (0,563) (frames with 0 names).
- **Surfaces:** plan-29 folder only; no disc, spool, encoder, checker or rule change.

### Phase 1 verification (Execute, cheap tier)

`witness_p1.py verdict` (entry point) on the live witnesses gives `verdict A`, drift none, concerns none.

- **G:** `4ed9cd80…`, re-hashed in full at 04:41 and unchanged.
  - L0 (0,541) leaf [928] frame at offset 197,597,600, length 320, sha256 `3c927c6b…51b48`.
  - Name record at offset 197,597,764, 144 B, sha256 `a681fcc4…6b92a`: class 288, string_type 6, raw (0,370), lat −38.727284749 / lon 90.0, Latin-1 text "France, Terres australes et antarctiques françaises, Îles Saint-Paul et Nouvelle-Amsterdam - Île Saint-Paul (eaux territoriales)".
- **Spool:** L0 (0,541) cell at offset 248,992,624, 2,616 B, sha256 `5b7c1a75…`. Record 0 column bytes sha256 `e2a39a45…`. lat −38.727285888 / lon 77.519035767, the same text in UTF-8. K1 nearest distance 1,635,904.94 raw (> 0.5). Not halo-eligible.
- **R** (`8c2d2027…`): all nine cells (0..1 × 540..542) are `empty_slot`, and ix −1 is outside coverage. Byte-equal names: **none**.
- Tip `assign_to_parcel` and the mesh twin both return `None` for this name. `git merge-base --is-ancestor 34a04cc 16e2931` exits 0.
- Whole-spool scan: 2,006,629 anchored names checked across all levels; plan-18-rejectable **1**, which is exactly the pinned item; 0 extras.

`artifact_feedback` was not called (workflow-service calls excluded by standing instruction).

**Phase 1 outcome verified: verdict A (G≠R; root cause O03, stale spool from pre-plan-18 extractor `34a04cc`).**

#### Carried

1. Phase 2 follows branch A: a route (a)/(b) candidate comparison, a new disc at a new path, live K1, R parity, a positive control, and provenance/OVERVIEW/3-90 note updates.
2. Observation for Design, out of scope here: G has two other non-empty L0 frames, at (0,562) and (0,563), in a block where R has none. They carry no names and no K1 failure. They are not investigated by this plan and are not absorbed.
3. The DESIGN's "spool lat −38.727284749" is G's decoded latitude. The spool holds −38.727285888 (same raw row). The plan record states this correction.

## Phase 2 — K1 exits 0 on the disc in force, with no relabel and parity recorded against R (branch A)

The approach is open. The invoker declared a route-(a)/(b) candidate comparison, scored against the fixed Phase 2 outcome and recorded in the plan record; no separate refine. Implementation is one unit, with its brief authored inline: `briefs/2-01-drop-guard-successor-oracle.md`. Execute runs the encode, K1, diff and tests under the guard.

### 2-01 — counted assembly drop guard and successor oracle (route (a))

- **Worker:** Codex `gpt-6.1-sol` (high), sandboxed. Report: `reports/2-01-drop-guard-successor-oracle.md`. Status: `done with concerns` (heavy gates deferred to Execute, by design).
- **Route comparison** (`phase2_routes.md`): (a), the counted assembly guard, scored 12; (b), cell-scoped spool regeneration, scored 7. Hybrid cell regeneration was rejected. (a) was chosen.
- **Built:**
  - `parser/kiwiw/cenc.py`: `E1Spool(guard_names=True)` uses private copy-on-write mappings and filters names outside the plan-18 lattice span (`name_drops`). The spool stays byte-untouched.
  - `parser/build_alldata.py`: drops are counted per level to stdout and to manifest `out_of_span_names_dropped`. In chunks with drops, a probe-and-pad step re-runs E2 on the unfiltered spool and zero-pads any shrunk frame to its original extent, so no later frame relocates. `_cenc.c` is unchanged.
  - Tools: `diff_disc.py`, `compare_k1.py`, and `witness_p1.py --successor`.
  - Tests: `parser/tests/test_name_drop_guard.py`, `parser/tests/test_successor_oracle_tools.py`.
  - The O03 note in `rules_other.json`.
- **Runs (Execute, guarded, `output/scratch-29/run_p2.{sh,log}`):**
  - Encode exited 0 (101 s): L0 drop 1, every other level 0, equal to Phase 1's prediction (1 rejectable name, at L0).
  - Successor sha `2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae`, 1,692,105,152 B (same size as `4ed9cd80…`).
  - `diff_disc`: 146 changed bytes, `confined_to_cell_0_541` true. Changed-leaf list: [L0 (0,541) leaf 928].
  - Live K1 `-j6` exited **0**.
  - G/R successor witnesses exited 0.
- **Execute amendment to `compare_k1.py` (deviation):** the first compare exited 1 because `range` checked fell by exactly 1. Every name anchor is also a range-check vertex (`parser/kiwiw/_k1.c` `range_item` for names). The expectation is now range checked −drops, with failing and worst error unchanged. The re-run (`runs/p2_compare_k1b.json`) gives pass True. DESIGN's "every other kind identical" did not foresee this coupling.
- **Full suite after 2-01:** 3 failed / 1055 passed / 7 skipped.
  - `test_perf_inventory` also fails on baseline `cc96570` (`runs/p2_tests_base3.json`), so it is pre-existing and carried.
  - `test_build_wiring::test_e1_e2_once_per_range` and `test_bench_record::test_bench_output_byte_identical_to_unbenched` were caused by the guard. Fixer brief `briefs/2-02-guard-accounting-fix.md`.

### 2-02 — guard accounting fix

- **Worker:** Codex hit its usage limit (about 05:11 AEST; resets 06:18 AEST) after adding two tests. **Execute finished the fix directly** (deviation). Report: `reports/2-02-guard-accounting-fix.md`.
- **Fix:**
  - `name_drops` filters by the build window rect, using the per-name cell index.
  - Job tuples carry the combined cell range.
  - E2 stats are captured before the probe.
  - Defect 3 confirmed: the synthetic fixture names are genuinely out of span.
- **Runs (`output/scratch-29/run_p2b.{sh,log}`):**
  - `test_name_drop_guard` + `test_build_wiring`: 12 passed.
  - Perth with plan-29 code is `04be2f6e0e700ee6d1022e370c2dffeba183c1d3c9299147d2238eeb920fb728`, equal to `perth_base` built at `cc96570`, with 0 drops at every level.
  - The AU re-encode `G_verify` equals `2ee3456a…` (110.9 s, peak 4.49 GB).

### Phase 2 verification (Execute)

Outcome A items:
1. O03 is absent (`witnesses/g_successor.json`: `o03_absent` true, leaf 928 names `[]`). Drops per level are L0 1 / others 0, equal to Phase 1's single rejectable name.
2. Successor at the new path `output/scratch-29/G_new/ALLDATA.KWI`, sha `2ee3456a9aeb8607b88be4edd989a2034dd7fdd6f7846369d9dbc4c8ff20e6ae`. The independent re-encode is identical. The diff against `4ed9cd80…` is 146 bytes, all inside the L0 (0,541) leaf [928] frame (`witnesses/successor_diff.json`).
   - Protected discs re-hashed unchanged: `4ed9cd80…` and `013586b5…`.
   - Spool fingerprint unchanged (`9541a10a…`).
   - `4ed9cd80…` stays the historical oracle.
3. Live K1 `-j6` exits **0**:
   - name_anchor 2,317,055 checked / 0 failing (checked −1);
   - completeness 1,800,514 / 0;
   - range checked −1 (coupled, see 2-01);
   - every other kind identical to `rem01_k1_live` (`witnesses/successor_k1_compare.json`, pass True).
4. R parity: R has no frames over the nine cells (all `empty_slot` / `outside_coverage`). The successor leaf 928 has zero names, so the names are equal. Named structural residual: G still has a (now nameless) L0 (0,541) leaf frame where R has an empty slot.
5. Perth: tip Perth `04be2f6e…` is unchanged by plan-29 code. DESIGN's `da13a775…` is the 3-11-era Perth (`scratch-3-11/perth_fix`), which tip already differed from before plan 29, so this is explained, not caused here. Goldens: in the full suite below.
6. Positive control: `test_quantisation_roundtrip.py::test_moved_road_node_and_name_are_caught` passes on both engines (an in-span misplaced name still fails name_anchor). It is also in the full suite.
7. Updated: `docs/provenance.md` (scratch-29 entry), the OVERVIEW WP1 disc-in-force sentence, the 3-90 brief successor-pin note, and the plan-27 pin ledger row.

Both branches:
- `rules_other.json` O03 note carries the disposition and the successor sha.
- No tolerance changed; no checker change.
- No 3-90 run, no plan 04 phases 4–6 or plan 06, and no Phase 3 close. 170 / 3-16 / 3-17 were not reseated.
- Full suite after 2-02 (`runs/p2_parser_tests2.json`, 605 s, peak 10.1 GB under the guard): **1 failed / 1060 passed / 7 skipped**. The only failure is the pre-existing `test_perf_inventory::test_inventory_covers_every_module` (modules missing from `perf_inventory.json`, which also fails at `cc96570`). Goldens, the bench and wiring tests, and the positive control pass.

`artifact_feedback` was not called (workflow-service calls excluded).

**Phase 2 outcome verified: branch A. K1 exits 0 on the successor disc in force `2ee3456a…`.**

#### Carried

1. `test_perf_inventory` fails on baseline too; it is pre-existing and not caused by plan 29.
2. G frames at L0 (0,562) / (0,563), and the now-nameless (0,541) frame, exist where R has empty slots. This structural difference goes to Design, not absorbed.
3. The probe-and-pad design keeps frame extents by zero-padding the shrunk leaf. That keeps the diff confined, but it is not R parity of frame layout.
4. The coupling of range checked to name anchors (−drops) is documented in `compare_k1.py`.
