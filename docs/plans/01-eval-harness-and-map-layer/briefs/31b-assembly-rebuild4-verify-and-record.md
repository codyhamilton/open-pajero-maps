# Brief: 31b -- Rebuild #4 (assembly only): verify and record

Consumer: implementation worker (fresh agent; do not resume 31's). Verification and documentation only.
Owned paths: `docs/plans/01-eval-harness-and-map-layer/PLAN.md` (append a "Build record (date)"
section only; no acceptance checkmarks), `docs/plans/01-eval-harness-and-map-layer/IMPLEMENTATION.md`
(append), `docs/design/target-disc.md` (only the WP1 ALLDATA.KWI map-layer row's deviations cell).
Code is read-only; if a check fails, report it, do not patch numbers.
Depends on: 31 (assembly finished, exit 0, no unexpected WARNING lines other than brief 29's
trim warnings). Runs alongside: nothing.

## Steps
1. Confirm 31's build finished: exit code, wall/RSS from `build.time.log`, new sha256 vs
   `16329332...` (must differ), manifest sha256/total_size agree.
2. `python parser/compare_disc.py --reference /run/media/codyh/464210-8480 --generated output/ALLDATA.KWI
   --report output/report.json` (~22 min). `pytest parser/tests -q`.
3. Expected: spotcheck PASS (28), mfde PASS (30), envelope sub-frame rows PASS (29) leaving only the two
   count residuals L0 name_count and L12 parcel_count (declared deviations, pending acceptance),
   container/decode/pointers/mht29/shape/vocab still PASS. Compare every level's parcel_count vs the 26b
   table (per-kind division adds divided leaves at L0/L2/L4/L8; report new ratios; all must remain in
   [0.5,2]x except L12).
4. Record: harness table, trim counters from `manifest.json` `trimmed_items` (per level/kind dropped
   totals and % of kind), capacity projection vs 4.7 GB, any residual FAIL with cause. Proposed (not
   self-accepted) deviations: L0 name_count 0.103x (26a evidence), L12 parcel_count G=3 vs R=1
   (see IMPLEMENTATION.md entry "Units 28-31").
## Report back
Pass/fail per check, residuals, trim totals, new sha256.
