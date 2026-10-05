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

## Phase 2 — Live pin contract for Phase 3 close is stated; historical 100/26650 disposed without invention

Refine skipped. One unit: `briefs/2-01-live-pin-contract.md`.

### 2-01 — live pin contract

- **Worker:** Codex `gpt-6.1-sol` (high), sandboxed, 08:05–~08:14 AEST, 89,962 tokens. Report: `reports/2-01-live-pin-contract.md`.
- **Built:** `pin_contract.py` (`publish`, light, no disc read), `pin_contract.tsv`/`.json`, `phase2_note.md`, and `parser/tests/test_pin_contract.py` (synthetic, 28 passed; Execute re-ran it, 28 passed). The worker ran `publish` itself; it reads only committed or retained JSON and verifies each sha256, so no guarded run was needed.
- **Result:** live failing is 0 for every K1 kind on `2ee3456a…` (background 176,386,506 checked; background_boundary 64,111,046; completeness 1,800,514; interior_cover 1,590,566; name_anchor 2,317,055; range 285,809,587; road_node 42,994,980; road_point 0; step 227,935,489), from plan 29's compare, corroborated by plan 32's K1 `-j6` report. Live contract: pinned set ∅ = live failing set ∅. `pinned_candidates.tsv`: digest, 100 shown groups and the 26,650 / 1,939,931 footer verified; no full enumerations recovered; disposition **residual-not-required-for-live-close**, historical identity unverifiable. No rows invented.

### Phase 2 verification (Execute, cheap tier)

1. `pin_contract.tsv`/`.json` give live failing counts per kind on the successor, cited with sha256; the live pinned-failure set is empty because failing is 0 everywhere; the set-equality rule for the live close is stated, and any missing or positive count keeps it open.
2. Historical `pinned_candidates.tsv`: sha256 verified; disposition `residual-not-required-for-live-close` with root cause (full enumerations were never committed; the live contract does not need them when the live set is ∅).
3. OVERVIEW's `pinned_candidates` set-equality blocker is narrowed accordingly.
4. Plan 04 Phase 3 is **not** closed; PSS remains a blocker.
5. No 3-90, no invented pin list, no later phases, no reseat.

`artifact_feedback` was not called (workflow-service calls excluded).

**Phase 2 outcome verified.**

## Remediation 01 — routed changed-cell completeness (REVIEW R1)

- **Worker:** brief `briefs/remediation-01.md`. Codex was at its usage limit
  (from ~08:23 until 11:19 AEST), so Execute (Grok Bot) implemented the fix
  and discloses that here. Re-review is a separate step.
- **Built:** `oracle_chain.py`:
  - `tree_leaves(..., footprint=True)` and `iter_frames(..., routed=True)`
    carry each leaf's exact absolute footprint;
  - `routed_signatures` signs, per base cell, the sorted (footprint,
    length, SHA-256) triples;
  - `routed-diff` reconciles the routed list with the retained multiset
    baseline. It verifies the baseline hop pins, the list hash and the
    count, and requires that no baseline cell is missing.

  `parser/tests/test_oracle_chain.py` adds the swap, footprint,
  relocation-plus-padding, superset and tamper tests (49 passed with
  `test_pin_contract.py`). Code commit: `c2cc6dc`.
- **Runs (guarded):** `output/scratch-31/rem01/run_rem01.{sh,log}`. AU
  finished in 226 s (RSS 140 MiB) and Perth in 0.4 s. Both exited 0, and
  the protected discs re-hashed unchanged.
- **Result:**
  - AU: 246,123 routed changed cells, Perth: 795.
  - Routed-only cells: **0** on both hops; baseline cells missing: 0.
  - Under routed footprint identity, the multiset lists are complete.
  - Evidence: `evidence/routed-3-14-{au,perth}.json` and `phase1_note.md`
    § Remediation 01.
- **OVERVIEW (R2):** the plan-31 sentence now names the evidence types:
  - the retained AU 3-11 list;
  - the measured AU and Perth 3-14 multiset and routed lists;
  - the reused plan-29 leaf proof.

  It carries AU 3-11's +60 B non-payload gap and the unmeasured 3-14
  container, index and padding scope as residuals.
