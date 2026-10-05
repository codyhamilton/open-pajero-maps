# Implementation — 32 other-kind classify joins

- Tool: orchestrator is the Execute background worker. Unit workers are Codex `gpt-6.1-sol` (high), sandboxed. Execute runs heavy steps under `parser/tools/run_heavy_python.py` (lock) and commits.
- DESIGN landed at `9fb00da`. Disc in force: successor `2ee3456a…` (plan 29; R absence proven on index bytes at `8798302`).
- Scratch: `output/scratch-32/`. Plan 04 Phase 3 is **not** closed by this plan; PSS and the close synthesis are out of scope.

## Phase 1 — Every in-scope kind has a successor failing-dump census

Refine skipped.

- **Execute heavy run** (`output/scratch-32/run_p1.{sh,log}`, 2026-10-06 06:52 AEST): `quantisation_roundtrip.py --disc output/scratch-29/G_new/ALLDATA.KWI -j 6 --engine c --dump-failures output/scratch-32/dump --dump-kinds interior_cover,name_anchor,background,background_boundary`. Exit 0, PASS in 83.1 s, PSS peak 7,303 MiB. The guard log is `runs/k1_dump.json` (memory_peak 5.94 GB).
  - Dump files: `background.bin`, `background_boundary.bin`, `interior_cover.bin` and `name_anchor.bin` are each 0 bytes (sha256 `e3b0c442…b855`). `dump_manifest.json` sha256 `c29ed9f0…6839`.
- Unit `briefs/1-01-census-and-empty-discharge.md` (one worker carries the Phase 1 census artefact and the Phase 2 empty-branch artefacts).

### 1-01 — census and empty discharge

- **Worker:** Codex `gpt-6.1-sol` (high), sandboxed, ~06:53–07:12 AEST, 79,946 tokens. Report: `reports/1-01-census-and-empty-discharge.md`.
- **Built:** `census.py` (`census`, `publish`), `phase1_note.md`, `phase2_disposition.md`, and `parser/tests/test_other_kind_census.py` (synthetic, 19 passed; Execute re-ran it, 19 passed).
- **Runs (Execute, guarded, `output/scratch-32/run_census.{sh,log}`):** `census` and `publish`, both exit 0 (20 MB peak). They generated `census.tsv`/`census.json` and the header-only `assignments/{interior_cover,name_anchor,background,background_boundary}_assignment.tsv` (plan 28 assignment columns, 0 rows).
- **Result:** every in-scope kind has 0 failing rows on `2ee3456a…`; branch **`all_live_empty`**; plan-29 compare control matches (0 failing).

### Phase 1 verification (Execute, cheap tier)

1. `census.tsv`/`.json`: kind, failing rows, dump path, bin/manifest sha256, workers 6, cgroup peak 5.94 GB (K1 run; PSS 7,303 MiB), disc pin `2ee3456a…`.
2. In-scope kinds are interior_cover, name_anchor, background and background_boundary; completeness is excluded with a pointer to plan 28.
3. Branch flag: `all_live_empty`.
4. Plan-29 control: failing counts match (0).
5. No classify recovery, no OVERVIEW blocker-clear claim, no PSS, no Phase 3 close.

`artifact_feedback` was not called (workflow-service calls excluded).

**Phase 1 outcome verified.**
