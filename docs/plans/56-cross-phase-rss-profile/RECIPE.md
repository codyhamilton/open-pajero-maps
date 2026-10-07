# Plan 56 — measurement recipe

## Caps (standing)

- Serial only: `flock /home/codyh/workspace/open-pajero-maps/output/.heavy.lock`
- Wrapper: `parser/tools/run_heavy_python.py --log output/scratch-56/runs/<phase>.json -- <argv>`
- Encode `-j4`; K1 ≤ `-j6`
- Clean-stop if RSS ≳ 17.5 GiB or MemAvailable ≲ 3 GiB
- Missing `memory.peak` → fail closed

## Phase catalog (Primary labels)

| Phase | Entrypoint (tip) | Default measure argv (stand-in first) | Full (when lock+time allow) |
| --- | --- | --- | --- |
| mass_decide | `docs/plans/04-c-core-orchestration/triage/historical_bg/p5_owner_exclusive/mass_decide.py` | `--r 8 --smoke-leaves 20 --cache-clear-every 10` | resume/full 95059 (cite plan 44 Unit 4c/4d peaks; optional re-measure) |
| control | `…/p5_owner_exclusive/control.py` | stratified n=200 seed=44 `--r-cap 8` (Gate A/B path) | same (bounded) |
| representability | `parser/tools/k1_representable.py` (or quantisation_roundtrip K1 caller) | labelled stand-in disc+spool pair; K1 ≤ `-j6` | full-AU only if explicitly seated |
| encode | `parser/build_alldata.py` via `parser/tools/bench_build.py` | Perth (or AU) `-j4` tree peak | AU census-style |
| dump/extend | `parser/tools/dump_join.py` / `bench_dump_memory.py finalize-run` | fixture finalize-run + windowed dump_io | live residual CLI if available |

## Ledger schema (per phase run)

JSON under `docs/plans/56-cross-phase-rss-profile/ledger/` + wrapper logs in `output/scratch-56/runs/`:

```json
{
  "schema": 1,
  "phase": "mass_decide|control|representability|encode|dump_extend",
  "label": "stand-in|full|cite_prior",
  "argv": [],
  "wall_s": 0,
  "max_rss_kib": 0,
  "memory_peak": 0,
  "memory_stat": {"anon": null, "file": null, "file_dirty": null},
  "tree_peak_mb": null,
  "residency": [
    {"class": "named", "evidence": "size_accounting|before_after_free|smaps|sampler", "kib": 0, "live_at_peak": true}
  ],
  "inter_phase_boundary": null,
  "notes": []
}
```

## Concurrent residency rule

Forbidden: “assumed freed.” Each residency row needs evidence (accounting, before/after free delta, smaps rollup, or sampler). At least one inter-phase free-then-reenter sample when two phases share a session.

## Inter-phase boundary sample (required once)

1. Finish phase A under wrapper; record peak + residency.
2. Force known frees (`clear_spool_caches`, close readers, drop caches if applicable).
3. Re-sample RSS/`memory.stat`.
4. Start phase B under same scope recipe; record whether A leftovers remain.

## Cite-prior allowed rows

Plan 44 mass OOM @30k (~17.1 GiB RSS) and chunk2 (~2 GiB) may be entered as `label=cite_prior` with pointers to Unit 4c/4d — still require at least one fresh stand-in mass_decide under this plan’s wrapper for co-residency tagging. Plan 48 encode tree peaks may seed encode row as cite_prior until a fresh bench_build lands.
