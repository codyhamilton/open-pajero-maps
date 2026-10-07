# Plan 47 implementation record

Run identity: Execute seat (Grok Bot executor, Cursor session), started 2026-10-07 13:01 AEST.
Design landed at `6a65cf9` (draft read at `6538530`). Master tip at start of execute after DESIGNs 48–53: `2563e47`. Refine skipped (approach known). Reviewer: OpenCode DeepSeek Flash only. Heavy runs serial under `flock output/.heavy.lock` via `run_heavy_python.py`, encode `-j4`, K1 ≤ `-j6`. Host evidence read in place from cited `scratch-14/p3/indep/` paths (Decision 2 CopyToBox equivalent on same host; no writes into those dirs).

## Phase 1: Key lists and set arithmetic

Units:
1. Commit surviving `old_dump_311` completeness key list (739) + sha; extract from retained bin.
2. Fresh K1@`1cf40f8` on `013586b5` (`scratch-3-11/G_new`), `-j4`, dump completeness; byte-equal after canonical sort vs retained.
3. Set-diff vs plan-28/776 (`dump_ext` / `per_rule` keys): 52 cleared, 89 added; locate 188 as subset of 739; verify 3-17 native-order identity where cited.
4. Update `residuals.tsv` for R-G8-2-b, R-G8-3-a, R-G8-4-d.

## Phase 2: Representability and legacy contract

(depends on Phase 1)

## Phase 3: The 89 root cause

(depends on Phase 1)


### Phase 1 verification (2026-10-07 AEST)

- keys/ committed under `triage/independent_reviews/3-15/conditions/keys/` (keys_739, keys_776, cleared_52, added_89, historic_188_in_739, set_arithmetic.json, old_dump_311.sha256, native_order_verify.json).
- Fresh K1@`1cf40f8` on `013586b5` (`scratch-3-11/G_new`), `-j4`, under heavy.lock via `run_heavy_python`: completeness failing **739**; fresh dump sha `c4d68769423f265d15c09e9dca234db1d81955ebb1c946e087655e430c398f3b` **byte-equal** to retained `old_dump_311/completeness.bin` (no canonical-sort delta).
- Set arithmetic: 739 − 52 + 89 = 776; identity_check.equals_776 true; historic 188 ⊂ 739 (188/188); added_89 equals setdiff.
- Native order: 188/188 `dump_row_original` match 3-17 note table 3-12 native rows (`native_order_verify.json`).
- Residuals R-G8-2-b, R-G8-3-a, R-G8-4-d discharged (plan 47 Phase 1).


### Flash review (Phase 1)

- Seat: OpenCode DeepSeek Flash (`opencode run -m deepseek/deepseek-flash`), 2026-10-07 ~13:57–14:00 AEST.
- Verdict: **PASS-WITH-CONCERNS**. All four Phase 1 claims independently verified.
- Concerns addressed / noted:
  1. R-G8-2-b identity rewrite: DESIGN close-text is key-list + set-diff (C2b/C2c). G2b stitch/frame-artifact limbs were not Phase 1 surfaces; left named in 3-15 REVIEW / residual close-text history; not re-proven here.
  2. 3-14 native-order half: recorded in `native_order_verify.json` (188/188 via `keys_776.dump_row_original`).
  3. 776 provenance via committed `keys_776.tsv` (= per_rule 776); scratch path cited only as decode source.
- Log: `output/scratch-47/runs/flash_p1.stdout`.


## Phase 2 — representability (Region+_required_cells) — 2026-10-07 ~15:17 AEST
- Engine: `run_representability_region.py` (Region ∪ tall + `_required_cells` + `k1_representable`).
- Historic 188: **faces 885 / meets 189 / in_cell 205 / representable 0** — **exact match** to 3-15 (`match_3_15_188: true`).
- Added 89: meets 90 / faces 625 / in_cell 137 / repr 0 (no 3-15 face target for 89; all not-representable).
- R-G8-2-a / R-G8-2-d regenerable from tables. Next: legacy-contract R-G8-2-c; Phase 3 r89.

## Phase 2 close (legacy contract) — 2026-10-07 ~15:34 AEST
- R-G8-2-a / R-G8-2-d: regenerable from `representability/table_{188,89}.tsv` (exact 885/189/205/0).
- R-G8-2-c: **unverifiable:producer_deleted** — see `representability/legacy_contract_r_g8_2_c.json`. Arithmetic 363+132+56+188=739 holds; no tracked producer.

## Phase 3 — r89 baseline + cause — 2026-10-07 ~15:34 AEST
- Baseline half R-G8-3-b: **89/89** padded-frame sha match vs disc `4ed9cd80…` (`r89/baseline_match.json`).
- Cause labels (`r89/cause_labels.json`): **89/89 chord-artefact** — legacy IB vertices lie outside the TSV-named source EO interior (xor pip); consistent with 3-16 0/89 counterfactual. No `valid-lost` / build-regression keys.
- R-DVD limb: `unverifiable:reference_disc_not_mounted`.
- Next: update residuals end-states; Flash review; close-out.
