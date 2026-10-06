# Implementation — 41 encoder/build close gates

Master direct. Phase 2 (light) landed before Phase 1 (heavy bench), by queue
order; the design marks both independent.

## Phase 2 — close-gate rule and checker

- **Classification (R-G8-5):** a **repo rule**. The trigger (encoder and
  build surfaces) and the command (`parser/tests` under `.venv-rp`) are
  specific to this repo.
  - The workflow plugin's close-out skill has no suite rule and names no
    project.
  - A generic plugin variant ("run the project's declared full suite before
    closing a phase that touches production code") is routed to the Workflow
    System Manager by the parent. It is not drafted here.
- **Rule:** `docs/WORKFLOW.md` § "Encoder/build close gates (plan 41)".
  - **Trigger:** the design-land..HEAD diff touches any of:
    - `parser/kiwiw/*.c` or `*.h`;
    - `parser/kiwiw/cenc.py`;
    - `parser/build_alldata.py`;
    - `parser/kiwiw/alldata_writer.py`;
    - `parser/kiwiw/disc.py`;
    - `parser/tests/fixtures/goldens/`.
  - **Gates:** IMPLEMENTATION quotes three marker lines before the
    phase-closing commit:
    - (a) the full suite summary line at the HEAD sha, with no failures or
      errors;
    - (b) the encode wall: median of three at `-j4`, spread, baseline;
    - (c) the AU / Perth sha gate.
- **Checker:** `parser/tools/close_gates.py --base <sha> [--head REV] --impl
  <path> [--impl-rev REV]`.
  - Light, no lock: one `git diff --name-only` and one text scan.
  - Output: JSON with the trigger paths, each gate's matched line, the
    missing gates and pass.
  - Exit codes: 0 pass or not triggered, 1 missing, 2 usage/git error.
  - `perf_inventory.json` entry: orchestration.
- **Tests:** `parser/tests/test_close_gates.py`, 9 tests:
  - all gates present;
  - a failing or erroring suite line is not gate (a);
  - each gate needs every field (5 cases);
  - trigger patterns;
  - the plan 34 worked example, skipped if that history is absent.

  `test_close_gates.py` + `test_perf_inventory.py`: 13 passed.
- **Worked examples** (`close_gates.py --impl-rev <close>`):

  | plan | base → close | trigger | result |
  |---|---|---|---|
  | 34 | `9fb00da` → `4ab27e8` (P2 close) | yes: `parser/build_alldata.py` | **missing (a), (b), (c)** (exit 1) |
  | 37 | `517781e` → `5facd75` (P2 close) | no | pass (exit 0) |
  | 41 P2 | `6e12b36` → this close | no (docs/tools only) | pass, not triggered |

  - **Plan 34:** in substance, (a) was never run (53 restricted tests: the
    missed `test_parcel_mask`), and (b) was not measured at close. The
    successor sha was recorded (`successor_sha.json`, Perth sha) but not as
    a gate line, so (c) is missing by the marker rule.
  - **Plan 41's own pass example** is its Phase 1 close. That phase touches
    `_cenc.c` only if a performance fix lands, and it quotes all three
    gates.
- **Residuals:** R-G8-5 is discharged (repo rule plus checker; plugin
  variant routed). R-G9-4 is owned by plan 41 Phase 1.
