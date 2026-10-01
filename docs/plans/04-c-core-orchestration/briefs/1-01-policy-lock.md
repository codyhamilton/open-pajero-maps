# Brief: 1-01 — Policy and contracts lock

Consumer: one Sonnet worker (Phase 1 is a single unit).
Owned paths: `docs/ARCHITECTURE.md`, `docs/plans/03-map-layer-parity-remediation/DESIGN.md` (a pointer block only), `parser/perf_inventory.json`, `parser/tests/test_perf_inventory.py`. Touch nothing else.
Commits: Commit to the current branch (`master`) when done evidence passes. Do not push.
Depends on: nothing.
Runs alongside: nothing.
Budget: about 14 files to read, about 450 lines changed (most of it the inventory), 60 tool turns. Past the budget, stop: write a handoff under this brief's name in `docs/plans/04-c-core-orchestration/IMPLEMENTATION.md` (done, not done, what you learned), commit it, and report `over budget`.

## Required reading, in order

1. `docs/plans/04-c-core-orchestration/DESIGN.md` — Intent, Solution Shape, all three Domains (the Contract bullets are binding), Architectural Implications, Phase 1 and the Surfaces/Outcomes of Phases 2–5 (they tell you which phase moves which module).
2. `docs/ARCHITECTURE.md` — the file you are changing; note "Module map", "Build boundary", "Evaluation".
3. `docs/plans/03-map-layer-parity-remediation/DESIGN.md` — only lines 338–520 (Contracts B, H, T, W) and the Phases 4–10 headings from line 745, to place the pointer and to see which text is superseded.
4. `parser/` — `ls` and grep imports to classify modules; `parser/tests/boundary.py` and one existing test for the house test style.

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

Make the "C for perf-sensitive work, Python orchestration only" rule and the libkiwiw boundary the stated architecture, mark plan 03's superseded text and frozen phases, and commit an inventory that classifies every `parser/` Python module and is enforced by a test.

## Contract

Cited from plan 04 `DESIGN.md`:

- Domain: Python orchestration → Contract: the definition of *perf-sensitive* ("any loop whose trip count scales with the vertices, shapes, parcels, frames or cells of a full-AU disc or spool"), "One door", and "Inventory: a committed inventory classifies every Python module under `parser/` as orchestration, C-now, C-later or retired; a test fails for any module absent from it."
- Domain: libkiwiw → Contract (granularity, D1, K1, census kernels, determinism, layout single-source, evidence, off-the-build-path) and Gates (the hard-gate list, H5/H6).
- Architectural Implications: the supersession list for plan 03 (Contract B's "Python owns … decoders" and "nothing else crosses" sentence, for verification only; Contract T layer (a)), and the freeze of plan 03's remaining Phase 3 units and Phases 4–10.
- Phase 1 Outcome (verbatim): "`docs/ARCHITECTURE.md` states the rule … and the libkiwiw boundary including D1, K1 and H5/H6; plan 03 `DESIGN.md` carries a pointer marking the superseded Contract B/T text and Phase 4–10 as frozen; the perf inventory exists and a test fails for any `parser/` Python module missing from it; every module classified C-now or retired names the phase that moves it. No code behaviour changes."

Settled, do not reopen: Decisions 1–9 and Assumptions 1–5 in plan 04 `DESIGN.md`. Extraction is a non-goal (Decision 9): classify its modules `c-later` with that reason.

## Changes

- **ARCHITECTURE.md.** Add the rule near the top (after Pipeline). Re-state "Build boundary (C)" as the libkiwiw boundary: the build entry points E1/E2/H4 as they are, plus D1, K1 and the census kernels described as the *planned* verification entry points, each marked with the plan 04 phase that builds it. Leave the module map describing the tree as it is today; add a line that Phases 2–5 change it and Phase 5 makes it true. Do not claim D1/K1 exist. Cite plan 04 `DESIGN.md` for the contracts; do not paraphrase them at length.
- **Plan 03 DESIGN.md.** One short block at the top (after the title, before Intent is fine): superseded by plan 04 — Contract B's decoder-ownership sentence and "nothing else crosses" sentence (verification only), Contract T layer (a); Phase 3's remaining units (3-10, 3-13, 3-05, 3-06) and Phases 4–10 are frozen until plan 04 Phase 6's successor design. Pointer only: edit no contract text.
- **`parser/perf_inventory.json`.** One entry per non-test `*.py` file under `parser/` (92 at HEAD; recount): path, class (`orchestration` | `c-now` | `c-later` | `retired`), phase (2–5, required for `c-now` and `retired`, else null), reason (one line, citing the perf-sensitive definition). Test modules under `parser/tests/` are covered by one glob entry of class `orchestration` (tests are not production paths; this is a deliberate narrowing of "every module" and is the only glob). Placement guide from the design's Phase Surfaces: the road/background/name/parcel decoders, their `*_writer.py`, `alldata_writer.py`'s R-replicate load path, `disc.py`, `roundtrip_*.py` → `retired`, phase 5 (a file that has both an orchestration part and a retired part is classified by the part that moves, reason says so); `quantisation_roundtrip.py` → `c-now`, phase 2; harness checks, census/overlay tools, `r_neighbours.py` → `c-now`, phase 4; extraction → `c-later`; CLIs, `cbuild`, `cenc`, `descriptor`, `frame_table`, `spool`, `report`, schema lint, volume/misc/parcel_mgmt header modules → `orchestration` unless a loop over full-AU data says otherwise. Classify the rest by the definition; when unsure choose `c-later` and say why. Do not move or edit any module.
- **`parser/tests/test_perf_inventory.py`.** Fails when: any non-test `parser/**/*.py` is missing from the inventory; an entry names a missing file; a class is outside the four; a `c-now`/`retired` entry has no phase in 2–5; a non-`c-now`/`retired` entry has a phase. Message names the offending paths. Follow the house style of an existing test file.

### Keep untouched

All Python and C source, goldens, `docs/schema/`, and every other part of the two docs. The build must be byte-identical by construction: your diff must contain no `parser/**/*.py` or `*.c` change except the one new test file.

## Done evidence

Write the test first; it fails (no inventory) before the inventory exists. Report its output before and after.

- `python -m pytest parser/tests/test_perf_inventory.py -q` → fails before; passes after.
- Temporarily add an empty `parser/kiwiw/_probe.py`: the test fails naming it; remove it and re-run: passes. Report both.
- `git diff --stat HEAD~1` (your commit) lists only the four owned paths.
- `python -m pytest parser/tests -q` → same pass count as before your change plus the new tests, 0 failed (about 3 minutes; run it in the background and wait for its end marker, per Contract W).
- `grep -n "D1\|K1" docs/ARCHITECTURE.md` shows them described as planned with phase numbers; `grep -n "plan 04\|04-c-core" docs/plans/03-map-layer-parity-remediation/DESIGN.md` shows the pointer.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then what changed, the check output before and after, any deviation from this brief and why, and any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently. List the inventory's class counts and any module whose class you chose with low confidence.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
