# Brief: 3-12 — re-measure overlap duplication cost after mult_const, trim if it still dominates

Consumer: 3-05, which builds the determinism matrix from the tree this unit leaves; 3-06, which runs the phase evidence against it.
Owned paths: `parser/kiwiw/overlap.py`, `parser/build_alldata.py` (only the overlap-merge call sites 3-09 added), `parser/tools/quantisation_roundtrip.py` (measurement only), and their tests under `parser/tests/` (`test_overlap.py`, `test_build_alldata*.py`). Touch nothing else; if a fix needs another file, report `needs context` before touching it.
Commits: Commit to the current branch when done evidence passes.
Depends on: 3-11.
Runs alongside: nothing.
Budget: 10 files to read, about 200 lines to change (0 if the finding is "no change needed" — that is an acceptable, complete outcome), 70 tool turns. Past the budget, stop: commit what passes, and report `over budget` with the handoff **in your report back, not in a file** — the orchestrator owns `IMPLEMENTATION.md`.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/IMPLEMENTATION.md` — the 3-09 entry in full (its evidence table and "Concerns"), and 3-11's entry once it exists (its before/after disc size and vertex counts).
2. `parser/kiwiw/overlap.py` module docstring in full (~lines 1-30) — the edge-cell vs interior-cell distinction, and `cover_ring`'s "5 points per cell" claim, which 3-11 may have changed the real cost of.
3. `parser/kiwiw/overlap.py` `build_level` (~line 303) — where `stats["interior_cells"]` and `stats["edge_cells"]` are counted; these are your baseline denominators.
4. `parser/build_alldata.py` — the call sites 3-09 added that merge borrowed shapes after mask fill (grep `overlap` in this file).

Read ranges and grep; do not read a whole file to find one section, and truncate long tool output.

## Goal

3-09 made every cell a background shape overlaps receive it, closing G's crossing-mirror gap from ~2% to R's 75–87%+. That is correct and stays. But it also multiplied G's background vertex count from 31M to 141M (3-09's own numbers) by writing borrowed copies into 3.49M cell instances, and R appears to avoid needing most of that scale of duplication structurally, by coarsening large homogeneous areas into fewer, bigger frames (the L0-sparse 4x4-aliased tile) rather than repeating the same shape's boundary into many fine cells. 3-11 should already have cut the *per-copy* cost sharply for the interior-cell case, since `overlap.py`'s interior-cell substitute ring is exactly the rectangle shape 3-11 makes cheap. Find out, with real numbers on the 3-11-rebuilt disc, whether duplication is now an acceptable cost or still the dominant one — and only if it is still dominant, make the minimal, provably-safe cut.

**Build wall time is a second, equally binding goal here, not just disc size.** Full-Australia assembly was 36.7 s at 3-07 and is a project-standing budget of "under about a minute is fine, anything over needs its cause identified" (the baseline before this phase's work was ~35 s). 3-09's own pre-pass over 708,857 shared shapes pushed assembly to 98.7 s — already over budget on its own, independent of the size question. If 3-11's disc is still over ~60 s, treat that as this unit's problem too: the interior-cell cut below, if it applies, should be evaluated for its effect on wall time as well as size, and if wall time is still over budget even with no further size-driven cut available, say so explicitly as a concern rather than letting it pass silently because the size clause was satisfied.

## Contract

- **Measure first, against the disc 3-11 left, not the pre-3-11 one.** Build full-Australia from `output/extract_timing/spool` and report: total size, wall time, background vertex count, and — broken out separately — how many vertices come from a cell's own shapes vs from borrowed (edge-cell and interior-cell) copies, per level. `overlap.py`'s manifest counts (`shared_shapes`, `edge_cells`, `interior_cells`) already give you the cell counts; get vertex-per-copy either from the manifest if it already records it, or by instrumenting a scratch run.
- **If the gap to R's ~1.53 GB is now closed or within the Phase 1 band (`parser/refdata/harness.json`) AND wall time is under ~60 s,** make no code change. Report the measurement, say so plainly, and commit nothing (or only the measurement's evidence if you choose to keep a script — do not invent a persisted evidence file this brief does not ask for; report the numbers in your report back). `done` with this finding is a complete, correct outcome — do not manufacture a change to have something to show. If size is fine but wall time is still over ~60 s, that alone is grounds to look at trimming the interior-cell pre-pass (below) even if the size argument alone would not have required it — report this explicitly as the reason for any change made.
- **If duplication is still the dominant remaining cost,** the only cut on the table is this: skip writing a borrowed copy into a **wholly-interior cell** when that cell already receives full coverage of the same shape's type through some other existing mechanism (e.g. the coverage mask fill `build_alldata.py` already applies "after mask fill" — check whether a mask-filled cell of the *same background type* as the borrowed shape would render identically with or without the extra copy). Prove it before cutting: a diff of decoded content for a sample of trimmed cells must show no visible/measurable change (same effective coverage), and the crossing/corner mirror probe (below) must not regress, since edge cells are never in scope for this cut — only interior cells, and only where redundant. Do not touch `edge_cells` handling under any circumstance; that is 3-09's fixed contract and this unit's done evidence checks it stays intact.
- **Do not re-open 3-09's cell-assignment or clip contracts.** This unit may only change *whether* an already-decided borrowed interior-cell copy gets written, never which cells are candidates, never the edge-cell path, never the clip/densify/mult pipeline (3-11's).
- Reference disc R is at `/run/media/codyh/464210-8480`. The spool is `output/extract_timing/spool`. Python is `.venv-rp/bin/python`. Put scratch under `output/scratch-3-12/` with `TMPDIR` set there. Never edit `.claude/worktrees/`.

### Keep untouched

`overlap.py`'s edge-cell detection and clipping, `clip.py`, `synth.py`'s mult selection (3-11's), `divide.py`, roads, names, `parser/harness/**`, `parser/refdata/**`, all plan documents.

## Done evidence

Identify or write the failing check before changing code, if you change any (e.g. a fixture with one shape covering several wholly-interior cells filled by the same background type via mask fill: before, N borrowed copies are written; after, they are skipped and decoded content is unchanged). Report its output before and after.

- `.venv-rp/bin/python -m pytest parser/tests -q` passes; report the counts before and after.
- A full assembly from `output/extract_timing/spool` at `-j 12` into scratch. Report its sha256, size, wall time, and the size delta from 3-11's disc and from R's ~1.53 GB. The Perth fixture must be identical at `-j 1` and `-j 4`; report its sha.
- `compare_disc.py --generated <new ALLDATA.KWI> --checks coord_scale --no-manifest --report <scratch>/cs_G.json` PASS.
- `quantisation_roundtrip.py --spool output/extract_timing/spool --out <scratch>/roundtrip.json`: report failing counts before and after — must not rise.
- Re-run the crossing/corner mirror probe (`output/research-3-bg/bg_edge_probe.py` or 3-09's equivalent) at the same sampled levels as 3-09 and 3-11 reported. **Crossing mirror must not regress from 3-09's numbers** — report them side by side.
- Before/after counts: `shared_shapes`, `edge_cells`, `interior_cells`, cells skipped as redundant (if any change was made), and total background vertices.

## Report back

Keep it under 1,500 tokens. Status is one of `done`, `done with concerns`, `blocked`, `needs context` or `over budget`. Lead with the measurement finding (gap closed / still open) before any code change description. Then give what changed (if anything), the check output before and after, the disc and Perth shas, any deviation and why, and any contradiction with the contracts or R evidence. Never resolve a contradiction silently. For a non-trivial bug outside your done evidence, report its symptom, location and root cause if found, and do not fix it here. Do not spawn agents beyond read-only research helpers.
