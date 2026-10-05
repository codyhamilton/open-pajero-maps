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
