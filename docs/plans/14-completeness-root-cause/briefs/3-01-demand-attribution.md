# Brief: 3-01 — Demand attribution (names the source behind dump_row 335)

Consumer: Codex `gpt-6.1-sol`, reasoning high, in worktree `/home/codyh/workspace/open-pajero-maps-14-completeness` (detached HEAD at the plan tip).
Owned paths: `docs/plans/04-c-core-orchestration/triage/demand_attribution_3-01.py`, `docs/plans/04-c-core-orchestration/triage/demand_attribution_3-01.tsv`, `docs/plans/04-c-core-orchestration/triage/demand_attribution_3-01.md`, `docs/plans/14-completeness-root-cause/reports/3-01-demand-attribution.md`, scratch under `output/scratch-14/attribution/` and `output/scratch-14/runs/`. Touch nothing else. In particular, edit no file under `parser/`.
Commits: Commit to the current detached HEAD when done evidence passes, with a plain-summary title and no trailer. Do not push.
Report: before committing, write `docs/plans/14-completeness-root-cause/reports/3-01-demand-attribution.md` (a handoff; rubric in `tools/quality/checks/execution-report.json`) and include it in the commit.
Depends on: nothing (Phase 2 closed at `8c37bae`).
Runs alongside: nothing (single worktree; heavy work is serialised).
Budget: 12 files to read, about 400 lines of new script, 60 tool turns. Past the budget, stop: write a handoff under this brief's name in `docs/plans/14-completeness-root-cause/IMPLEMENTATION.md` (done, not done, what you learned), commit, and report `over budget`.

## Required reading, in order

1. `docs/plans/14-completeness-root-cause/DESIGN.md` — "Phase 3" and its "Phase 3 refine" record and Units table.
2. `docs/plans/04-c-core-orchestration/triage/phase2_open_questions.md` — Q-source-335 (discriminators tried, untested hypotheses).
3. `parser/kiwiw/_k1_cmp.c` — the whole file (188 lines): branches (a), (b), and (c), plus the cell list.
4. `parser/tools/quantisation_roundtrip.py` — `Region.__init__` (:446–503, including the **tall-shape** selection and the ±1 halo), `Region.inside` (:540–597; note the `TOL` slack along the scan line), and the completeness block of `_check_block` plus `_required_cells` (:1026–1100).
5. `docs/plans/04-c-core-orchestration/triage/complete_repair_2-02.py` — `decompose_eo_faces`, `encoder_piece_densified`, `CProbe`, `source_attrs`, `cell_b4` (reuse these by import; do not copy them).
6. `parser/tools/run_heavy_python.py` — usage (`--log`, `--cwd`, `--lock`).

Read ranges and grep; do not read a whole file to find one section, do not re-read a file already in context, and truncate long tool output.

## Goal

For every failing completeness key on the disc in force, name each region shape that makes the checker demand that key: shape identity, branch (a/b/c), and whether its in-cell footprint is representable under the builder contract. dump_row 335's demanding shape must be named. This table is the exact prediction that 3-03's checker change is measured against.

## Contract

- DESIGN Phase 3 lists "Unproven rows remain open questions". Phase 2 left `Q-source-335` open because no a/b/c source was found within ±32 cells. Its record names two untested hypotheses: a demanding ring homed more than 32 cells away, and `region.inside` semantics that differ from strict per-ring even-odd.
- Settled by refine: the demand is defined by the checker as it runs, not by a re-derived rule. Build the attribution from the oracle's own `Region` for the block that checks the key: same level, same block rectangle `c0..c1, r0..r1`, same halo, and the same tall-shape selection. Evaluate (a) and (b) exactly as `_required_cells` does, and (c) exactly as `Region.inside` does, including `TOL`. The C path in `_k1_cmp.c` is documented as Python-equal (`parser/tests/test_k1_completeness.py`). If the two disagree on any key, report it as a finding, not a fix.
- "Representable" means the Phase 2 contract: EO faces of the source ring (`decompose_eo_faces`), each clipped to the target cell, then `encoder_piece_densified(face, mc)` with the source's own `mc`, then production C `bg_shape` via `CProbe`. A footprint is representable if and only if production C gives ≥1 record for the target cell. Also record the mirror's verdict; if mirror and C disagree, that is a finding.
- Disc in force: `output/scratch-14/G_new/ALLDATA.KWI`, sha256 `4ed9cd801bdd7099…`. Spool: `output/extract_timing/spool`. Key universe: the 776 rows of `output/scratch-14/dump_raw/` (equal to `triage/completeness_evidence.tsv`).

## Changes

- New `triage/demand_attribution_3-01.py`:
  - Takes `--keys` (a dump_row list, or `all`) and `--max-keys`.
  - Resolves each key to the checking block in the same way `quantisation_roundtrip.py` enumerates blocks.
  - Builds `Region` and computes the full demander set per key.
  - Writes one TSV row per (key, demander) and a JSON proof per key under `output/scratch-14/attribution/`.
  - A key with zero demanders is an error row; it must not be silently dropped.
- TSV columns: `dump_row, level, ix, iy, type, block, shape_ref` (home cell + ordinal, or tall id + home cell), `branch` (a|b|c), `c_tol_only` (the (c) hit holds only because of `TOL`: strict even-odd says outside), `mirror_emits`, `c_records`, `representable`.
- Then one derived per-key column: `all_demanders_unrepresentable`.
- `demand_attribution_3-01.md`:
  - States the 335 answer: the shape, its geometry summary, and why ±32 missed it.
  - Gives the per-branch counts and the count of keys where every demander is unrepresentable (the 3-03 prediction).
  - Lists any key with a representable demander. Each of those is a build-defect candidate and must be named, not grouped.
- Run order:
  1. 335 alone.
  2. `--max-keys 25`, to measure the per-key cost.
  3. All 776.
- Every run goes through `run_heavy_python.py --log output/scratch-14/runs/attribution_<n>.json`. If the 25-key run projects ≥10 min for all 776, stop after committing the 335 result and report `done with concerns` with the projection; the orchestrator splits the rest.

### Keep untouched

- All `parser/` sources, all Phase 1/2 triage artefacts, and the protected outputs: `output/scratch-3-11/G_new` (sha `013586b5…`), `output/scratch-14/G_new/ALLDATA.KWI` (`4ed9cd80…`), and `output/extract_timing/spool`.
- Never delete anything under an `output` path. `output` is a symlink into the main checkout.

## Done evidence

Identify or write the failing check before changing code. Report its output before and after.

- `run_heavy_python.py … demand_attribution_3-01.py --keys 335` → exit 0, ≥1 demander named for dump_row 335, with branch and representability.
- `… --keys all` → 776/776 keys with ≥1 demander, and 0 error rows. If not, each error row is listed in the note.
- Self-check inside the script: for each key, the union of demanded (cell, type) pairs for its block, recomputed through `_required_cells` itself, contains the key. Assert it.
- `sha256sum` of the two protected discs is unchanged before and after (record both).

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. Then:
- what changed;
- the 335 answer;
- the per-branch counts;
- the `all_demanders_unrepresentable` count and the list of exceptions;
- the check output before and after;
- any deviation from this brief and why;
- any contradiction between this brief and the contracts it cites. Never resolve a contradiction silently.

A non-trivial bug outside your done evidence: report symptom, location, and root cause if found. Do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
