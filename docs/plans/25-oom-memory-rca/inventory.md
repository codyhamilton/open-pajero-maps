# Plan 25 Phase 1 — Incident inventory

**Incident name (stable):** plan-14 completeness heavy OpenCode stopped for OOM

**CHM hold:** heavy Maps jobs (including further plan-14 completeness seats) remain
on hold until plan 25 outcomes land **and** CHM clears the hold. Landing this plan
does **not** auto-clear.

**Stopped job class (measurement label):** plan-14 completeness OpenCode path —
Phase 2-style heavy Python under `flock output/.heavy.lock` (cell-local /
complete-repair / related R+G+spool decode). Distinct from plan-05 residual /
finalize / s07 / triage **fixture** classes.

**Host evidence (copied):** `host-evidence-2026-10-06.md` (from
`/workspace/maps-oom-2026-10-06.md`). Kernel OOM 2026-10-06 ~00:19 Brisbane;
victim `cursor` pid 2626982; largest RSS `python` pid **2881900 ≈6612 MiB anon**;
pipeline bash|python|tail; start ~00:16:50 in Flash **2-02** window; **not**
`cell_local_2-01.py` (finished ~00:14 under flock). Exact argv unrecoverable.

## Master surfaces — proves / does not prove

| Surface | Proves | Does not prove vs this stop |
| --- | --- | --- |
| Plan **05** `docs/plans/05-heavy-job-memory.md` | Windowed dump_join / finalize / 3-07 / triage cut peak RSS + `memory.peak` on fixtures; lock + scoped `systemd-run` | That plan-14 completeness OpenCode class is safe; no gate for cell_local/complete-repair |
| Plan **17** `docs/plans/17-live-extend-dump-join.md` | Live extend → tracked `dump_join` | Completeness OpenCode peaks |
| Plan **14** Phase 1 `IMPLEMENTATION.md` | Flock full-AU encode + `-j6` completeness dump → 776 rows; oracle `4ed9cd80…` | Peak RSS / `memory.peak` for encode, dump, or Phase 2 units |
| Plan **14** Phase 2 unit **2-01** (closed) | Cell-local membership science packet | Memory profile of the OpenCode seat CHM stopped |
| Plan **20** `docs/plans/20-reconcile-pss-ops-cap.md` | PSS ceiling 9,726,501 kB absolute; ops ≤ `-j 6` | Host oomd stop ≠ PSS contract; bar not cleared |
| `docs/WORKFLOW.md` Heavy jobs / `docs/ARCHITECTURE.md` oomd | One heavy under lock; RSS vs `memory.peak`; siblings can die first | Hold-lift criteria for *this* CHM hold |
| Plan **23** (on master after this inventory’s ground tip moved) | Graphics copy-through cmp | Unrelated to OOM class |

**Cody Assumption 5 override (2026-10-06):** land concrete guards in this plan
(Flash argv+peak wrapper; bound/stream plan-14 triage loads) — not harness-only.
