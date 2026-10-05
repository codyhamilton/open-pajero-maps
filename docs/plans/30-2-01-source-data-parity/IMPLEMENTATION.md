# Implementation — 30 2-01 source-data parity

- Tool: orchestrator is the Execute background worker. Unit workers are Codex `gpt-6.1-sol` (reasoning high) via `codex exec -s workspace-write`, one seat at a time. Sandboxed workers leave changes in the tree; Execute runs heavy steps under `parser/tools/run_heavy_python.py` (takes `output/.heavy.lock`) and commits. If Codex is usage-limited, Execute does the unit itself and says so here.
- Session: queued after plan 29 (Cody's approval, 2026-10-06 06:33 AEST). DESIGN landed at `3447b39`.
- Worktree: `/home/codyh/workspace/open-pajero-maps-14-completeness` (detached; fast-forward pushes to `master`).
- Scratch: `output/scratch-30/` (run logs in `output/scratch-30/runs/`).
- Disc in force: successor `2ee3456a…`. Historical control `4ed9cd80…`. R pin `8c2d2027…`. Plan 29 R1 remediation runs in parallel and does not touch this plan's 2-01 cells.
- Protected, byte-untouched: `output/scratch-14/G_new`, `output/scratch-3-11/G_new`, `output/scratch-29/G_new`, `output/extract_timing/spool`, and the R disc (read-only mount).

## Phase 1 — Every 2-01 row is fingerprinted; type census and 288-template identity are proven

Refine skipped (DESIGN). One unit: `briefs/1-01-fingerprint-census.md`.

### 1-01 — fingerprint, census and template proof

- **Worker:** Codex `gpt-6.1-sol` (high), sandboxed, 06:36–06:47 AEST, 94,451 tokens. Report: `reports/1-01-fingerprint-census.md`.
- **Built:** `fingerprint.py` (subcommands `census`, `--disc` probe, `merge`), `fingerprint.tsv` (342 rows), `fingerprint_summary.json` (sha256 for all 688 inputs), `phase1_note.md`, and `parser/tests/test_parity_fingerprint.py` (synthetic, 22 passed).
- **Runs (Execute, guarded, `output/scratch-30/run_p1.{sh,log}`):** successor and historical disc probes exit 0, each with its full pin verified. Both give demanded-type total 0. The historical control equals the membership TSV. Merge exit 0.
- **Execute append-only wording corrections** (census 341 × 288 + 1 × 321): plan-14 record follow-up, `phase3_groups.md`, `per_rule_phase2_reconciliation.md`. OVERVIEW wording is deferred to Phase 2's narrowing.

### Phase 1 verification (Execute, cheap tier)

1. `fingerprint.tsv` covers 342 rows. It joins to the members TSV, `phase3_membership.tsv` and the plan-28 join (O01 340, O05 2: rows 246 and 567).
2. Census: **341 × 288 + 1 × 321 (dump_row 246, L0 (834,886))**.
3. 288 template: **341/341** have one cell-local 13-vertex polygon, branch c, span 1/12° × 1/8° (5′ × 7.5′, tolerance 1e-9°). Two signatures: **T1 191** (north-west start) and **T2 150** (south-west start). Exceptions: 0. Correction to DESIGN Ground: both have the *same* counter-clockwise winding and differ only in start corner.
4. Bands (bbox midpoint, descriptive): west 85, east 86, south_offshore 129, other 42.
5. G demanded-type count is 0 on successor `2ee3456a…` and on historical `4ed9cd80…`, for all 342 rows.
6. Heavy steps ran through `run_heavy_python.py` (lock), with logs in `output/scratch-30/runs/`.
7. R provenance: the retained scratch-14 decoded-coordinate proofs, sha-pinned. There was no fresh R-disc read; DESIGN Contract 6 prefers light reuse.

`artifact_feedback` was not called (workflow-service calls excluded).

**Phase 1 outcome verified.**
