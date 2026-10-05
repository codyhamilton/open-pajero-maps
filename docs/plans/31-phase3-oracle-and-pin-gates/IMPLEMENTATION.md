# Implementation — 31 Phase 3 oracle chain and pin gates (slice 1)

- Tool: orchestrator is the Execute background worker. Unit workers are Codex `gpt-6.1-sol` (high), sandboxed `workspace-write`. Execute runs heavy steps under `parser/tools/run_heavy_python.py` (lock) and commits. If Codex is usage-limited, Execute does the unit and says so here.
- DESIGN landed at `b831244`. Disc in force: successor `2ee3456a…` (plan 29 verdict A, re-proven on R index bytes at `8798302`).
- Scratch: `output/scratch-31/`. Protected discs (`87a01b14…` if found, `013586b5…`, `4ed9cd80…`, `2ee3456a…`) and the spool are read-only.
- Plan 04 Phase 3 is **not** closed by this plan.

## Phase 1 — Every disc-in-force re-oracle hop has an exact changed-cell (or leaf) proof

Refine skipped. One unit: `briefs/1-01-oracle-chain.md`.

### 1-01 — oracle chain

- **Worker:** Codex `gpt-6.1-sol` (high), sandboxed, ~06:52–07:10 AEST, 144,412 tokens. Report: `reports/1-01-oracle-chain.md`.
- **Built:** `oracle_chain.py` (`check-census`, `diff`, `publish`), `oracle_chain.tsv`/`.json` (six hop rows), `phase1_note.md`, and `parser/tests/test_oracle_chain.py` (synthetic, 16 passed; Execute re-ran it, 16 passed).
- **Runs (Execute, guarded, `output/scratch-31/run_p1.{sh,log}`):** 3-11 census audit, AU and Perth 3-14 diffs, publish. All exit 0; discs re-hashed unchanged.
- **Result:**
  - AU 3-11 (`87a01b14…`→`013586b5…`): 37 L0 cells, 37/37 predicted, 0 unexplained (retained list, hash verified).
  - AU 3-14 (`013586b5…`→`4ed9cd80…`): **246,123 changed cells** measured (L0 244,060 / L2 1,944 / L6 118 / L8 1); causes unattributed.
  - Perth 3-14 (`da13a775…`→`04be2f6e…`): **795 changed cells** (L0 784 / L2 11); causes unattributed.
  - AU plan 29 (`4ed9cd80…`→`2ee3456a…`): 1 L0 cell (0,541), leaf 928, 146 bytes, 0 unexplained.
  - Perth 3-11 and plan 29: unchanged (recorded equality).

### Phase 1 verification (Execute, cheap tier)

1. `oracle_chain.tsv` covers `87a01b14…→013586b5…`, `013586b5…→4ed9cd80…` and `4ed9cd80…→2ee3456a…` with full digests, artefact path and sha256, changed count, confinement claim and unexplained count (plus Perth rows).
2. Unexplained: 3-11 0; plan 29 0; 3-14 AU 246,123 and Perth 795, each listed by cell in the sha-pinned retained lists, with the open reason "payload causes not measured" (DESIGN Outcome 2's "named with why it is open").
3. OVERVIEW's "3-11 versus 3-14 oracle" wording is narrowed to "3-14 oracle cause attribution", with the measured identities and the table link.
4. Protected discs re-hashed unchanged after the read-only diffs (`protected_unchanged: true`).
5. No Phase 3 close, PSS, other-kind joins, 3-90 brief or later phases.

`artifact_feedback` was not called (workflow-service calls excluded).

**Phase 1 outcome verified**, with the 3-14 cause attribution carried as a named residual.
