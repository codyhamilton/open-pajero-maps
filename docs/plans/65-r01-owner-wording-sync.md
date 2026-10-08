# R-G5-4-a/b/c owner wording synced to plan 44's record (docs-only)

Plan 65 is docs-only. It brings the `residuals.tsv` owner/evidence text for R-G5-4-a, R-G5-4-b and R-G5-4-c in line
with plan 44's record, and points the OVERVIEW ownership cells at plan 62. No discharge state changed. No waiver
language. It landed before plan 62 Phase 3, as Design required.

## Intent
Plan 60 follow-up: the R-G5-4-a/b owner wording lagged plan 44 ("or a waiver", "confirm checker"), and
R-G5-4-c's wording read as "optional". Cody's bar applies: no waivers, and carried is not closed.

## What Was Built
Land commit `6032bce`:
- `residuals.tsv` R-G5-4-a / R-G5-4-b:
  - "UPDATED by plan 44" text appended to `count_or_identity` and `evidence`;
  - `owner` replaced with "plan 44 (closed owner; … not discharged) → Design: plan 62".
- `residuals.tsv` R-G5-4-c: `owner` replaced with "plan 45 (closed) → Design: plan 62 (… carried is not closed)".
- `blocking` cells byte-unchanged on all three rows.
- `docs/OVERVIEW.md` L85 / L86 / L95:
  - plan 44's row now reads "87,743 proven-fixed but not discharged; 7,316 rows → plan 62 (in Execute)";
  - the plan-46 children are routed to Design drafts 63 / 64;
  - R-G5-4-c is in plan 62's scope.
- Plan 44 a/b split by `src`:
  - a: 87,648 build; residual 6,486 = 3,023 outside@16 + 2,783 ambiguous + 525 skip_divided + 118 no-OE + 37 source-removed;
  - b: 95 build; residual 830 = 432 source-removed + 193 outside@16 + 189 ambiguous + 16 skip_divided.
- Sha pins: `phase2_decisions_full.tsv.gz` 3d221b6f…, `phase2_residuals_still_outside_r16.tsv` d11bcae8…,
  `inventory_925.json` 10166eb1…, `phase2_summary_full.json` 26d6fc92….

## Review
Flash (`deepseek/deepseek-flash`): **LAND**, claims A–G pass, with the numbers and shas recomputed. One non-blocking concern:
OVERVIEW L108 still says 62 is a box draft. That line is outside this contract, and plan 62 Phase 3 refreshes it.

## Residual Risks
- None in the rows themselves; no discharge state changed.
- Plan 44's folder is still not collapsed into a record. Named here; left to a close-out.

## Follow-ups
Plan 62 Phase 3 appends its results after this wording and refreshes OVERVIEW L108.

Scratch: `output/scratch-65/` (Flash review prompt/logs; regenerable).
