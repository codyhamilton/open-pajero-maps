# Brief: 33c -- Rebuild #6 (assembly only): verify and record

Consumer: implementation worker (fresh agent). Verification and documentation only. Owned paths: `PLAN.md`
(append "Build record (date, rebuild #6)" only; no acceptance checkmarks), `IMPLEMENTATION.md` (append),
`docs/design/target-disc.md` (only the WP1 ALLDATA.KWI map-layer row's deviations cell). Code read-only.
Depends on: 33b (exit 0).
## Steps
1. Confirm build: exit code, wall/RSS from `/tmp/wp1-unit33-logs/build.time.log`, sha256 differs from
   `c978b840...`, manifest sha256/total_size agree.
2. `.venv-rp/bin/python parser/compare_disc.py --reference /run/media/codyh/464210-8480 --generated
   output/ALLDATA.KWI --report output/report.json` (~22 min). `pytest parser/tests -q`.
3. Expected: spotcheck 14/14; envelope only L0 name_count and L12 parcel_count; L8 road max <= 99,794. Record
   every kind max vs R, name/parcel counts, trim table (L8 road %, L0 bg, L8 name; >1% blockers), halo_names,
   capacity vs 4.7 GB, max frame bytes.
4. Record proposed (not self-accepted) deviations: L0 name_count, L12 parcel_count, L0 bg / L8 name trim >1%.
   Give the WP1 acceptance evaluation.
## Report back
Pass/fail per check, residuals, trim + halo totals, new sha256.
