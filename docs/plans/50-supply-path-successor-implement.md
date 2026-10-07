# Successor implement for the 341 plan-30 supply-path rows (R-G9-2)

Plan 50 closed **R-G9-2**: overlay assembler supplies code-288 presence for all
**341** plan-30 supply-path rows. Successor AU oracle **`aeae426c…`**; diff vs
prior tip oracle **`88bd7852…`** is **341 changed / 0 added / 0 removed** (exact
target set). Row 246 untouched. Perth `04be2f6e…` unchanged. No Phase 3
product-close.

## Intent
Cody standing rule (2026-10-05). Presence parity, not geometry clone. Overlay
preferred. No plan 04 P4–6; no 3-90; no Cody-hold waivers; wall ≪60 s report-only.

## Why This Existed
Plan 30 left 341 rows at `verdict=supply-path` with production-C witnesses.
Plan 38 closed only row 246. Live extract treats multipolygon relations as
outer-ring ways only; the demanded marine-park / EEZ supply needed assembled
relations clipped per target cell.

## What Was Built
**Assembler / overlay**
- `parser/tools/supply_path_assembler.py` + tests
- `triage/source_parity/implement/` — targets_341, relation_members_10, snapshot
  ways pin (`2ad438fc…`, 16 ways of r2647638), overlay builder, phase1 proof,
  successor oracle record + cells TSV
- Overlay spool: 8 L0 merges + 333 inserts; L2–12 symlink to pinned extract

**Inputs:** Geofabrik `australia-260824.osm.pbf` for 338 rows; narrow attic
extract for the 16 missing ways of r2647638 (rows 396/397/775). Full snapshot
`39a836dd…` was absent at start; DESIGN allows that equivalent.

**Oracle / gates**
| Item | Result |
| --- | --- |
| AU sha | `aeae426cc62b183a9f041418a0a9980ba596ef43cc9123e0c4ef30dbfb591221` |
| Diff vs `88bd7852` | 341 changed, 0 added, 0 removed; set == targets |
| G presence code 288 | 341/341 |
| Encode `-j4` wall | 44.23 s (report-only) |
| K1 `-j6` | failing 0 |
| Suite | 1490 passed, 9 skipped |
| disposition | 341 → `implemented` |
| residuals R-G9-2 | `discharged-plan-50` |
| `oracle_chain` | AU hop plan 50; disc_in_force → `aeae426c…` |
| eo_census | guard_hits=0 |

## Review
Flash: **PASS-WITH-CONCERNS** → **LAND** (suite green + provenance
`disc_in_force` aligned at close). Soft concerns kept: narrow attic pin vs full
`39a836dd`; wall median-of-5 not run.

## Residual Risks
- Overlay not yet promoted into the live extract path (byte-stable rebuilds still
  need the overlay spool).
- Soft: narrow 16-way attic pin (witness coords match plan-30 production-C).

## Follow-ups
Parent may start 51–53. No Phase 3 product-close from this unit.

Scratch: `output/scratch-50/` (regenerable; G_new + spool_overlay protected).
