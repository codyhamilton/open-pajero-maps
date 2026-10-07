# Plan 44 implementation record

Run identity: Execute seat (Grok Bot executor, Cursor session), started 2026-10-07 12:38 AEST. Design landed at `c765afe` (draft read at `6538530`). Master direct at `6276350` (plan 43 closed). Refine skipped per Decision (approach known). Reviewer seat: OpenCode DeepSeek Flash only (`opencode run -m deepseek/deepseek-flash`, disclosed). Heavy runs serial under `flock output/.heavy.lock` via `run_heavy_python.py`, encode `-j4`, K1 ≤ `-j6`.

## Phase 1: Owner-exclusive tool landed and controlled

Units (orchestrator-direct; one brief each, committed before work):
1. `bg_owner_exclusive` tool + synthetic tests + perf-inventory
2. 925-row checker-rationale inventory (Ruling 3)
3. Control re-test of plan 39 identity-proven sample


### Unit 1 — `bg_owner_exclusive` tool (done)

- Surface: `parser/tools/bg_owner_exclusive.py` (compile_probe + probe_bg_flex with tc/b4/cr, clip_ring, wire_vertices, owner_exclusive_vertices, find_producer, bbox_meets_rect).
- Tests: `parser/tests/test_bg_owner_exclusive.py` — 7 passed.
- `parser/perf_inventory.json` triage entry added.
- Probes: scratch-44 `probe_flex_*` against `_cenc_33006aa.c` / `_cenc_d35b565.c`.

### Unit 2 — 925-row checker-rationale inventory (done)

- `triage/historical_bg/p5_owner_exclusive/inventory_925.{py,json}`: 925 rows, 0 keep-checker with per-row proof, all 925 join the owner-exclusive test. Citations scanned; R01 sample witness and `in_eo_same` ruled out as proofs (DESIGN).


### Unit 3 — Control re-test (STOPPED — systematic disagreement)

- Script: `triage/historical_bg/p5_owner_exclusive/control.py` (flex probes, neighbourhood spool lookup, disc-sourced verts; `dump_pre311` not retained on host).
- Smoke n=12: rate 0.25. Home-with-backgrounds n=60: rate 0.3167; all fails `prod_none`; OE limb 100% when producer unique.
- Analysis: `p5_owner_exclusive/control_analysis.md`. Identity-proven R01 shapes are often EO fragments (byte ≠ full-leaf `33006aa` clip of the geometric source).
- **Phase 1 stopped per DESIGN control gate.** Phase 2 not started. No residuals.tsv update. Carried: R-G5-4-a/b unchanged; Design must revise producer/control before Phase 2.

### Carried into later plans

- Drafts 48–53 staged at `output/scratch-44/maps-drafts-48-53/` (read at `607e5b6`; sha256 in `META.txt`). Land after 44 unblocks / after 48–49 per queue.
- R-G9-4 / R-G8-1-a Cody-pending (no waiver). R-G5-5 maps-parity-carried.


### Unit 3b — Fragment-producer + revised-contract control (stopped)

- Design revision landed at `1b839e3` (unique-byte | unique-fragment; cascade 45/46).
- Tool commit `ef00c12`: `identity_bearing_vertices`, unique-fragment; synthetic tests 9 passed.
- Stratified control n=200 seed=44 under revised producer: **rate 0.757576** (150/198 evaluable); CONTROL_FAIL vs ≥0.99.
- Agree: 91 unique-fragment + 59 unique-byte. All 48 disagrees `producer_none` (no-cover under nbhd=1; see `control_analysis.md`).
- Phase 1 not closed. Phase 2 not started. Design escalated with no-cover diagnosis.


### Unit 3c — DESIGN revision 2 (Gates A+B; expanding Moore)

- Second DESIGN revision landed at `92cd35f` (cascade 45/46). Assump-1 marked wrong; full-set ≥99% agreement-rate retired.
- Control rewrite `2e936e4`: per-row expanding Moore 1→R_cap=8 until unique-byte|unique-fragment; Gate A (OE≥99% among resolved); Gate B (100% class coverage with RC incl. `producer_home_outside_R_cap`); `offset_census.json`.
- Smoke + stratified n=200 under expanding search next; Phase 1 closes only when Gate A and Gate B both pass. Propose R in IMPLEMENTATION after census for Design confirm before Phase 2.
- Do **not** hardcode neighbourhood=1 or "enable 3×3" (nb=1 already was Assump-1; recovered 0/48).


### Unit 3d — Phase 1 CLOSED (Gates A+B); proposed R=8 for Design confirm

- Stratified control n=200 seed=44 `--r-cap 8`: Gate A **191/191 OE (rate 1.0)**; Gate B **198/198** (73 unique-byte, 118 unique-fragment, 7 `producer_home_outside_R_cap`).
- Offset census: max recovering radius **8**; by_radius 1→150, 2→16, 3→9, 4→6, 5→6, 6→3, 8→1.
- **Proposed Phase 2 default R = 8** (max recovering radius among unique-* per DESIGN Decision 5). Awaiting Design confirm before Phase 2 mass run.
- 7 outside-R_cap rows listed in `triage/historical_bg/p5_owner_exclusive/phase2_residuals_outside_R_cap.tsv` → named Phase 2 residuals / R-G5-4 children.
- R-G5-4-a/b still open.
- Designs 45/46: wait for Design confirm of R.


### Flash review (Phase 1 close) — 2026-10-07 ~15:00 AEST
- Seat: OpenCode DeepSeek Flash (`opencode run -m deepseek/deepseek-flash`).
- Verdict: **PASS-WITH-CONCERNS**.
- Gate A confirmed 191/191 OE rate 1.0 (re-ran control byte-identical).
- Gate B confirmed 198/198 (73/118/7); cover unchanged.
- Proposed R=8 **ACCEPT** (max recovering radius among unique-*).
- Concerns: R=8 equals R_cap (right-censored); outside_R_cap RC is search-bound not existence proof. Flag for Design when confirming R.
- Transcript: `output/scratch-44/runs/flash_p1.stdout`.


### Unit 4 — Design confirmed R=8; Phase 2 open (2026-10-07 15:09 AEST)

- Design confirmed locked Phase 2 default **R=8** (Decision 5; max recovering radius among unique-* in Phase 1 census).
- Right-censor protocol (Flash concern): before final residual classification of the 7 `producer_home_outside_R_cap` (and any new from mass run), one-shot widen probe **R_widen=16** on that residual set only. If ≥20 new recovers at radius >8 → STOP for Design. Still-failing at 16 keep `producer_home_outside_R_cap` with max_radius=16 + counts.
- Phase 2 mass run: R-G5-4-a (94,134) + joined R-G5-4-b (925) under locked R=8. Cover/OE unchanged.
- Designs 45/46 may use locked R=8.
