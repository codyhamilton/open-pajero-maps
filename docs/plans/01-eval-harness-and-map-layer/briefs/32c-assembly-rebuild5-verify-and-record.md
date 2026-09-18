# Brief: 32c -- Rebuild #5 (assembly only): verify and record

Consumer: implementation worker (fresh agent; do not resume 32b's). Verification and documentation only.
Owned paths: `docs/plans/01-eval-harness-and-map-layer/PLAN.md` (append "Build record (date, rebuild #5)"
only; no acceptance checkmarks), `IMPLEMENTATION.md` (append), `docs/design/target-disc.md` (only the WP1
ALLDATA.KWI map-layer row's deviations cell). Code read-only; report failures, do not patch numbers.
Depends on: 32b (exit 0). Runs alongside: nothing.

## Steps
1. Confirm build: exit code, wall/RSS from `build.time.log`, new sha256 differs from `ed2d37ec...`, manifest
   sha256/total_size agree. No `hard 131,070-byte ceiling` warnings of the old form (all fallbacks now say
   "hard-ceiling fallback ... (brief 32)").
2. `python parser/compare_disc.py --reference /run/media/codyh/464210-8480 --generated output/ALLDATA.KWI
   --report output/report.json` (~22 min). `pytest parser/tests -q`.
3. Expected: spotcheck 14/14 (Perth Hay, Adelaide Pulteney); envelope only L0 name_count and L12 parcel_count;
   others PASS. Record every sub-frame kind max vs R (esp. L0 bg, L8 road, L8 bg), name_count per level (halo
   raises L0 only; L2-L10 unchanged within [0.5,2]x), parcel_count vs the rebuild #4 table.
4. Record: harness table, `trimmed_items` (fallback drops now included; state L8 road/L0 bg/L8 name % and the
   >1% blockers: L0 bg, L8 name, L8 road if any), `halo_names` per level, capacity vs 4.7 GB, max frame bytes
   per level (brief 30 caveat), residual FAILs. Proposed (not self-accepted) deviations: L0 name_count,
   L12 parcel_count, L0 bg / L8 name trim >1%. Give the WP1 acceptance evaluation.
## Report back
Pass/fail per check, residuals, trim + halo totals, new sha256.
