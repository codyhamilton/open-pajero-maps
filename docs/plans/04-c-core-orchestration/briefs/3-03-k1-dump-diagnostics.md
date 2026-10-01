# Brief: 3-03 — Diagnostic columns on the background-family dump rows

Consumer: 3-05 (classification predicates run over these columns), 3-07 (cause table for background and background_boundary).
Owned paths: `parser/kiwiw/_k1.h`, `parser/kiwiw/_k1.c`, `parser/kiwiw/_k1_bg.c`, `parser/kiwiw/cenc.py` (K1 section only), `parser/tools/quantisation_roundtrip.py` (dump section only), `parser/tests/test_k1_dump.py`, `docs/provenance.md` (extend the 3-02 entry). Touch nothing else.
Commits: Commit to `master` and push when done evidence passes.
Depends on: 3-02.
Runs alongside: 3-06 only.
Tier: Flash (mandatory Sonnet 5.5 review). RE-risky (high): geometry in C whose diagnostics decide the cause table. Ask the orchestrator for a stronger worker if Flash cannot make the fixture equality test pass in 40 turns.
Budget: 7 files to read, about 350 lines changed (about 220 C, 60 Python, 70 test), 70 tool turns. Past the budget, stop; write a handoff under this brief's name in `IMPLEMENTATION.md`; commit what passes; report `over budget`.

## Required reading, in order

1. `docs/plans/04-c-core-orchestration/DESIGN.md` — K1 check, Determinism, Layout single-source; Gates (120 s, PSS ceiling).
2. `docs/plans/04-c-core-orchestration/briefs/3-02-k1-failure-dump.md` — the dump row and flags you extend.
3. `parser/kiwiw/_k1_bg.c` — whole file (447 lines): shape index, `outline_distance`, `inside` (lines about 280-310), the three kinds.
4. `parser/kiwiw/_k1.h` — `k1_shapes`, `k1_tallrow`, `k1_ctx`, `K1_F_DUMP`.
5. `parser/tools/quantisation_roundtrip.py` — `Region.inside` (about 534-600) and `outline_distance` (read only; the oracle).
6. `output/scratch-3C-04/dbg1.py`, `dbg2.py` — how the 3C-04 triage probed polygon 65623 (winding vs parity, nearest vertices, max segment).

## Goal

Every dump row of kinds `background`, `background_boundary` and `interior_cover` carries cheap, fixed-width facts about why it failed and which spool shape is nearest, so a classifier can partition the 18 million rows with column predicates only. Verdicts and counts stay exactly as they are.

## Contract

Cited from `DESIGN.md`: "Counts are exact; only samples are capped." and "**Layout single-source.** Every row layout is declared once in a C header and mirrored in Python by a checked descriptor". Diagnostics never change a verdict: a unit test asserts it.

Decisions this brief makes (do not reopen). New dump columns (append to `K1_F_DUMP`; non-applicable = the stated sentinel):

| column | type | meaning | sentinel |
|---|---|---|---|
| `onb` | u8 | frame-boundary mask: bit0 vx==0, bit1 vx==4096, bit2 vy==0, bit3 vy==4096 | 0 |
| `d_any` | f64 | min Chebyshev distance to the outline of ANY-type spool shape, searched within radius 2.0 raw | NaN (none within 2.0) |
| `any_type` | i32 | type of that nearest any-type outline | -1 |
| `in_eo_same` | u8 | even-odd inside some same-type shape (the checker's rule, no tolerance) | 0/1 |
| `in_wn_same` | u8 | non-zero winding inside some same-type shape | 0/1 |
| `in_eo_any` | u8 | even-odd inside some shape of any type | 0/1 |
| `src_ix`,`src_iy` | i32 | home cell of the nearest same-type shape found within 64.0 raw of the vertex (for `interior_cover`: of the shape nearest to the cover centre within 64.0 raw) | INT32_MIN |
| `src_rec` | i32 | that shape's record ordinal inside its home cell's spool background column | -1 |
| `src_tall` | u8 | that shape came from the tall set | 0/1 |
| `src_nv` | i32 | its vertex count | -1 |
| `src_maxseg` | f64 | its longest edge length in raw (closing edge included for class-2 rings) | NaN |
| `d_src` | f64 | Chebyshev distance from the vertex to that shape's outline | NaN |
| `dcls`,`dnv` | i32 | the DISC shape's class and vertex count (from D1) | -1 |

- Nearest means smallest Chebyshev distance, ties broken by smaller (`src_iy`, `src_ix`, `src_rec`). `in_wn_same` uses the standard crossing-number with winding sign, double arithmetic, `-ffp-contract=off`.
- Computed ONLY for rows that are emitted into the dump (failing items) and only when the dump is on. Verdict code paths are not edited except to expose the shape ordinal and home cell.
- The 64.0 and 2.0 radii are constants in `_k1.h` (`K1_DIAG_SAME`, `K1_DIAG_ANY`). If no same-type shape is within 64.0, `src_*` keep their sentinels (the classifier treats that as "no source within 64 raw"). Do not enlarge the radius to chase them.
- If the nearest-shape search over 16.5 million rows makes the full-disc dump exceed 600 s wall, stop and report `blocked` with the measured rate rather than lowering the radii silently.

## Changes

- `_k1.h`: append the columns and the two radius constants. `_k1_bg.c`: a `k1_diag_fill(ctx, row, kind, vx, vy)` helper called at the dump emit sites of the three kinds; reuse the existing index. `cenc.py`/driver: descriptor and manifest field list updated; nothing else.
- Home cell and record ordinal of every shape in `k1_shapes` must be carried (extend the shape builder additively: arrays `hx`,`hy`,`rec`); local shapes get their spool cell and index within the cell.

### Keep untouched

Counting, verdicts, samples, 3-02's identity columns and file layout (columns are appended only), dump-off behaviour and wall.

## Done evidence

Extend `parser/tests/test_k1_dump.py` first (fails before: missing columns).

- Fixture tests on `bg_wrong_type` (`d_any` ≈ 0, `any_type` = the spool type), `bg_outside` (`in_eo_same`=0, `src_*` sentinel), `bg_long_edge` (`src_maxseg` equals the closing edge length computed independently in the test), `bg_tall` (`src_tall`=1), `bg_boundary_displaced` (`onb` nonzero, `d_src` ≈ 8), and one row per column asserted against a numpy computation written in the test for the same fixture (winding vs parity on the self-overlapping fixture you add: `bg_bowtie`, a figure-eight ring where the two differ).
- Verdicts: `.venv-rp/bin/python -m pytest parser/tests/test_k1_dump.py parser/tests/test_k1_background.py parser/tests/test_k1_points.py parser/tests/test_k1_completeness.py parser/tests/test_goldens.py parser/tests/test_perf_inventory.py -q --basetemp=output/scratch-3-03/pytest` → pass.
- Full-disc dump on G under the heavy lock (command as in 3-02, output `output/scratch-3-03/dump`, report `output/scratch-3-03/k1_dump.json`): manifest row counts equal the 3-02 counts; `totals` equal `output/scratch-2-07/k1_a.json`; the first 5 rows per level of each kind equal the corresponding 3-02 rows on the shared columns (`cmp` of the prefix of `output/scratch-3-02/dump/*.bin` rows, shared columns only); wall ≤ 600 s; `-j 1` vs `-j 12` byte-equal on `--levels 6`.
- Report a first look, no interpretation: per kind and level, the count of rows with `d_any` not NaN, with `in_eo_any`=1, with `in_wn_same`≠`in_eo_same`, with `src_ix` sentinel (computed with a 10-line numpy script on the dump files).

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. What changed, the check output before and after, any deviation and why, any contradiction with the cited contracts. Never resolve a contradiction silently. A non-trivial bug outside your evidence: symptom, location, root cause if found; do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.

## Amendments (orchestrator, 2026-10-02, after Flash run)

- `bg_outside`: its moved vertex is 30 raw out, inside `K1_DIAG_SAME` = 64, so a same-type source exists; `src_*` is the sentinel only beyond 64. The test asserts that.
- `bg_long_edge` is a clean fixture (no dump rows); the `src_maxseg` assertions moved to `bg_boundary_displaced` (10240) and `bg_tall_displaced` (18432).
- `bg_bowtie`: a symmetric figure-eight cancels (wn = 0), so a self-overlapping pentagram (centre wn = 2, eo = 0) is used; defined in `test_k1_dump.py` because `k1_fixtures.py` is not owned.
- `k1_diag_fill` takes the lattice search point (not frame-raw `vx/vy`), and inside tests use a horizontal ray with the checker's even-odd pairing and no TOL.
