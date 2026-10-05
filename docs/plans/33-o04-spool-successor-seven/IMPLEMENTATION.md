# Implementation — 33 seven O04 spool successor rows

- Tool: orchestrator is the Execute background worker. Unit workers are Codex `gpt-6.1-sol` (high), sandboxed. Execute runs heavy steps under `parser/tools/run_heavy_python.py` (lock) and commits.
- DESIGN landed at `9fb00da`, amended before landing to Design's ruling: **no default verdict**, and a per-row byte/decode witness that G and R are both absent.
- Disc in force: successor `2ee3456a…`. Historical control `4ed9cd80…`. R `8c2d2027…`. R absence must be proven from index sentinels or decoded frames, never from a lookup failure (plan 29 remediation-01 contract).
- Scratch: `output/scratch-33/`. Plan 04 Phase 3 is not closed by this plan.

## Phase 1 — Presence parity and O04 identity confirmed for all seven

Refine skipped. Unit `briefs/1-01-presence-witness.md`.

### 1-01 — per-row G/R presence witness

- **Worker:** Codex `gpt-6.1-sol` (high), sandboxed, 07:16–~07:23 AEST, 104,400 tokens. Report: `reports/1-01-presence-witness.md`.
- **Built:** `presence_witness.py` (`--disc g_successor|g_historical|r` probes, `publish`), `presence_witness.tsv`/`.json`, `phase1_note.md`, and `parser/tests/test_o04_presence_witness.py` (synthetic, 31 passed; Execute re-ran it, 31 passed). It reuses plan 29's hardened reader (`triage/name_anchor/witness_p1.py`).
- **Runs (Execute, guarded, `output/scratch-33/run_p1.{sh,log}`):** three disc probes and publish, all exit 0.
- **Result:** 7/7 rows `absence-proven` (demanded type count 0 on G successor, G historical and R; every slot resolved with frame bytes and decoded type counts); 0 exceptions. O04/spool identity reaffirmed from the plan-28 TSVs with hashes.

### Phase 1 verification (Execute, cheap tier)

1. `presence_witness.tsv` has seven rows (138, 236, 282, 284, 317, 496, 563) with native key, dump_row, demander id, O04 proof refs and hashes, stratum (emit-piece 138/284/496; demand-removed 236/282/317/563), R presence and G type counts on both discs.
2. All seven reaffirm R absent and O04/spool; exceptions: none.
3. No spool edit, no disposition verdicts, no Phase 3 close.

`artifact_feedback` was not called (workflow-service calls excluded).

**Phase 1 outcome verified.**

## Phase 2 — Each row closed as proven-non-deviation or fix-landed

Refine skipped. Unit `briefs/2-01-disposition.md`. Execute owns the OVERVIEW and plan-28 follow-up narrowing.

### 2-01 — per-row disposition

- **Worker:** Codex `gpt-6.1-sol` (high), sandboxed, 08:13–~08:20 AEST, 86,240 tokens. Report: `reports/2-01-disposition.md`.
- **Built:** `disposition.py` (`publish`, light), `disposition.tsv`/`.json`, `phase2_note.md`, and `parser/tests/test_o04_disposition.py` (synthetic, 50 passed; Execute re-ran it, 50 passed). Tests cover lookup_failed, non-zero counts, missing witnesses and hash mismatches.
- **Run (Execute):** `publish`, exit 0, 48 MiB RSS, output byte-identical to the worker's (tsv `b26795c1…`, json `64c8b624…`). It reads only committed JSON and was run under `prlimit` without the heavy lock, because another project's job held the shared lock and this step is not heavy.
- **Result:** all seven rows (138, 236, 282, 284, 317, 496, 563) **proven-non-deviation**, each on its own Phase 1 witness: demanded type count 0 on G successor, G historical and R, slots resolved with frame bytes. K1 completeness on `2ee3456a…`: 1,800,514 checked / 0 failing (plan 29 compare, cited with sha256). No `fix-landed`: emitting the emit-piece counterfactuals (138, 284, 496) would invent presence that R lacks. The O04 spool-hygiene observation is retained as evidence only.

### Phase 2 verification (Execute, cheap tier)

1. `disposition.tsv`: verdict, rationale, witness refs and hashes, fix artefacts (none), and K1 completeness failing (0) per row.
2. Emit-piece stratum (138, 284, 496): each is `proven-non-deviation` with its own per-row G/R absence witness; no default verdict was applied (Decision 3, amended).
3. Demand-removed stratum (236, 282, 317, 563): `proven-non-deviation` on the same rule.
4. `conflict-open` = 0.
5. OVERVIEW's O04 wording and the plan-28 follow-up are narrowed (the latter append-only). Plan 04 Phase 3 is not closed.

`artifact_feedback` was not called (workflow-service calls excluded).

**Phase 2 outcome verified.**
