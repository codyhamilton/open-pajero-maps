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
