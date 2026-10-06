# Brief: 2-01 — classify the six modules missing from parser/perf_inventory.json

Consumer: Codex `gpt-6.1-sol` (high), sandboxed.

Owned paths:
- `parser/perf_inventory.json` (six new entries only);
- `docs/plans/37-3-17-f2-identity-and-perf-inventory/reports/2-01-perf-inventory.md` (new).

Commits: none.

## Outcome (DESIGN Phase 2)

1. Read each module, then classify it under the inventory's own definition
   (read the file header and `parser/tests/test_perf_inventory.py`). A
   module is perf-sensitive when it has a loop whose trip count scales with
   full-AU vertices, shapes, parcels, frames or cells. Use only
   `orchestration` or `c-later` (with no phase). Give each entry a reason
   drawn from the code. A module that would need `c-now` with a phase is
   classified `c-later` and named in the report as a plan 04 Phase 4/5
   input. The six modules:
   - `parser/harness/checks/copy_through.py`
   - `parser/harness/checks/wp_na.py`
   - `parser/kiwiw/state_partitions.py`
   - `parser/tools/k1_representable.py`
   - `parser/tools/run_heavy_python.py`
   - `parser/tools/whole_file_guard.py`
2. `parser/tests/test_perf_inventory.py` passes 4/4. Run it with
   `--basetemp output/scratch-37/tests`. Do not change the test.
3. Do not run the full suite; Execute runs it under the heavy guard.
