# Report 2-01 — six modules classified in parser/perf_inventory.json

Seat: **Execute (Grok Bot), not Codex.** The Codex `gpt-6.1-sol` seat launched
at 11:23 AEST died at the Codex usage limit (weekly cap; the CLI reports a reset
at 2026-10-10 11:50 AEST, log `output/scratch-37/p1p2.codex.log`) before
editing anything. Execute did the unit from the brief and read every module.

Definition used (inventory `_doc` and plan 04 DESIGN): perf-sensitive = a loop
whose trip count scales with the vertices, shapes, parcels, frames or cells of
a full-AU disc or spool. Classes allowed by the brief: `orchestration` or
`c-later` with `phase: null`.

| Module | Class | Reason (from the code) |
|---|---|---|
| `parser/harness/checks/copy_through.py` | orchestration | Loop over the fixed 10 copy-through basenames; whole-file byte compare of those small sibling files; `_first_diff_offset` byte loop only on a mismatch. Never touches ALLDATA frames/parcels/cells. |
| `parser/harness/checks/wp_na.py` | orchestration | Three sentinel `Check` rows whose `run()` returns NA; no data loop. |
| `parser/kiwiw/state_partitions.py` | orchestration | Seven-row state/suffix table from `parser/refdata/state_partitions.json` (`lru_cache`); loops bounded by 7. |
| `parser/tools/k1_representable.py` | **c-later** | Python EO-face / wire representability mirror: per-ring-vertex exact `Fraction` loops (`_contacts` is O(n²) per ring; face walk; densify). Imported only by `quantisation_roundtrip._check_block` (line 1033), the `--engine python` count oracle, and called only for absent (cell, type) pairs; the default `--engine c` path uses `_k1_cmp.c` (`docs/design/k1-completeness.md` L30). Per-vertex scaling meets the definition, so `c-later` with no phase. |
| `parser/tools/run_heavy_python.py` | orchestration | flock + `systemd-run --scope` + `/usr/bin/time -v` + cgroup `memory.peak` log; loops bounded by argv, cgroup stat keys and time lines. |
| `parser/tools/whole_file_guard.py` | orchestration | `stat` size vs threshold, then `read_bytes` below it; no loop. |

Plan 04 Phase 4/5 input (named, not drawn): `parser/tools/k1_representable.py`
belongs with the `--engine python` oracle functions listed in the
`quantisation_roundtrip.py` entry that "Phase 5 deletes". Whether the Python
mirror is deleted or kept as the independent test oracle for
`test_k1_completeness_representable.py` is a Phase 5 decision.

Diff: 36 inserted lines in `parser/perf_inventory.json` (six entries, each
inserted after its directory neighbours); no existing entry changed.

Test (about 11:33 AEST): `PYTHONDONTWRITEBYTECODE=1 .venv-rp/bin/python -B -m pytest
-q -p no:cacheprovider parser/tests/test_perf_inventory.py --basetemp
output/scratch-37/tests` → **4 passed** (before: 1 failed / 3 passed, the
six modules listed as missing).
