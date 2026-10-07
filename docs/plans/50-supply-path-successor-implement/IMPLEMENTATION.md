# Plan 50 — IMPLEMENTATION

## Outcome

Successor implement for the 341 plan-30 supply-path rows (R-G9-2). Overlay path
chosen. Presence parity on successor G for **341/341** cells. Diff vs live
oracle `88bd7852…` is **341 changed / 0 added / 0 removed**, all L0, exactly the
target set. New AU sha `aeae426c…`. Perth untouched. No Phase 3 product-close.

## Path choice

Pinned **overlay spool** (`output/scratch-50/spool_overlay`): L0 rewritten with
8 merges + 333 inserts of cell-clipped supply backgrounds; levels 2–12
symlinked to `output/extract_timing/spool`. Live extract unchanged. Promote to
live extract only if a later unit needs byte-stable rebuilds without the
overlay dir.

## Assembler

- `parser/tools/supply_path_assembler.py` — assemble 10 relations (EO holes),
  clip to target cell, emit code-288 `BackgroundShape`.
- Inputs: Geofabrik `australia-260824.osm.pbf` ways for 338 rows; narrow
  date-matched attic extract of the 16 missing ways of r2647638
  (`implement/snapshot_ways_pin.json`, sha `2ad438fc…`) for rows 396/397/775.
  Full 61-relation snapshot `39a836dd…` was absent from disk at start; DESIGN
  allows an equivalent extract of those 16 ways.
- `triage/source_parity/implement/` — targets, pins, phase1 proof, overlay builder.
- Tests: `parser/tests/test_supply_path_assembler.py`.

## Phase 1

Stratified sample (≥1 cell/relation incl. 396/397/775): production-C presence
all true (`output/scratch-50/phase1/stratified_proof.json`). Snapshot rows
bytes match plan-30 witnesses (20 / 20 / 218).

## Phase 2

| Step | Result |
|------|--------|
| Overlay spool | 341 bgs; 8 merge + 333 insert |
| Clip presence | 341/341 |
| AU encode `-j4` | wall **44.23 s** (encode 36.8 s); report-only vs ≪60 s Cody hold |
| G presence type 288 | **341/341** |
| Diff vs `88bd7852` | **341 changed, 0 added, 0 removed**; set == targets |
| New AU sha | `aeae426cc62b183a9f041418a0a9980ba596ef43cc9123e0c4ef30dbfb591221` |
| eo_census | guard_hits=0 declines=0 |
| disposition | 341 → `implemented`; row 246 untouched |
| residuals R-G9-2 | discharged (successor implement landed) |

## Gates

- Suite: **1490 passed, 9 skipped** in 661.99s (`output/scratch-50/runs/suite_final.txt`) at `41a8de7ddeac`.
- K1: **failing 0** all kinds (`output/scratch-50/phase2/k1_au.json`), engine c, `-j6`, overlay spool; wall 78.5 s.
- close_gates: run at land (encoder/build surfaces: assembler is orchestration-only overlay; inventory entry only).
- Flash: **PASS-WITH-CONCERNS** → HOLD cleared after suite green + provenance disc_in_force aligned (`output/scratch-50/runs/flash_review.stdout`). Re-check: LAND PASS-WITH-CONCERNS (narrow attic pin D; wall report-only).
- Wall median-of-5: **not run**; single-run `-j4` wall **44.23 s** reported only (Cody hold ≪60 s not claimed).

## Non-goals held

No plan 04 P4–6; no 3-90; no Phase 3 product-close; no waivers; row 246 left;
no wholesale OSM import; wall budget not claimed.
