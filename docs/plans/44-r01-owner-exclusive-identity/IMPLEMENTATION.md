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


### Unit 3b — Fragment-producer + revised-contract control (in flight)

- Design revision landed at `1b839e3` (unique-byte | unique-fragment; cascade 45/46).
- Tool commit `ef00c12`: `identity_bearing_vertices`, unique-fragment; synthetic tests 9 passed.
- Control accepts unique-byte|unique-fragment. Spot-check `(0,1980,896)` shapes 1–2 → unique-fragment.
- Stratified control re-run under flock next; Phase 1 closes only on ≥99%.
