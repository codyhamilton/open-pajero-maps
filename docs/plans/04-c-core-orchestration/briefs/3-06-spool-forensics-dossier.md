# Brief: 3-06 — Forensic dossier: polygon 65623 and name_anchor L0 cell (0,541)

Consumer: 3-07 (background family cause table) and 3-08 (name_anchor and disc-defect classification).
Owned paths: `output/scratch-3-06/` only (git-ignored). No repo file changes; `docs/provenance.md` gets one entry only if you leave a script there that later units must re-run (then commit and push that edit).
Commits: None expected (see above).
Depends on: nothing.
Runs alongside: any other Phase 3 unit (it reads the spool and disc, runs no C build and edits no repo source). Hold `flock output/.heavy.lock` for any single step expected to take more than 60 s.
Tier: Flash (mandatory Sonnet 5.5 review). RE-risky (moderate to high): it reads polygon rings and decoded pieces and must report facts without interpreting. If Flash cannot answer questions D1 to D3 within budget the orchestrator should hand it to a stronger worker.
Budget: 8 files to read, scripts of about 250 lines in total, 60 tool turns. Past the budget, stop and report `over budget` with the answered questions.

## Required reading, in order

1. `docs/plans/03-map-layer-parity-remediation/briefs/3C-04-roundtrip-redesign.md` — the Amendment, findings 2, 3, 6.
2. `output/scratch-3C-04/probe_band.py`, `dbg1.py`, `dbg2.py`, `dbg3.py` — the 3C-04 probes. They name `65623` as a Region-local shape index of the block key `(0, 38, 15, 6, 2, 7, 1)`; that number has no meaning outside that Region. Part of your job is to say what spool shape it is.
3. `parser/tools/quantisation_roundtrip.py` — `Shapes`, `Region` construction (how local plus tall shapes are listed and numbered), `key_cells`, `_cells_to_shapes`.
4. `parser/kiwiw/spool.py` — `SpoolReader`; `output/scratch-2-07/k1_a.json` — the name_anchor sample (cell [0,541], leaf path [928], raw (0,370), lat -38.727284749 lon 90.0).
5. `docs/provenance.md` — G (`output/scratch-3-11/G/ALLDATA.KWI`) and the spool (`output/extract_timing/spool`).

## Goal

Answer the questions D1 to D8 below with measured facts (numbers, ids, paths), each with the exact command or script that produced it. No classification into checker/build/spool: that is 3-07's and 3-08's job. A fact you cannot establish is reported as `unestablished` with the blocker.

## Contract

Cited from `DESIGN.md` Phase 3: "The disc defect near spool polygon 65623 is classified in the cause table" and "`name_anchor`'s one failure (L0 cell (0,541), leaf 928) is such a carried spool item (the 3C record calls it an extractor defect)". The classes are: "checker rule wrong, build (disc) defect, or spool/extraction defect". Python only; `.venv-rp/bin/python`; the 2-04 equality tests prove the K1 verdicts equal the Python tool's, so Python helpers from the tool are valid for reading shapes.

Questions (answer each in `output/scratch-3-06/dossier.md`, a table of question, answer, command):

- D1: Reconstruct the Region of block key `(0, 38, 15, 6, 2, 7, 1)` as `dbg1.py` does and identify shape #65623: its type, class, vertex count, HOME CELL (ix, iy), record ordinal inside that cell's spool background column, whether it is a tall shape, its bounding box in raw and in cells, and whether the ring is closed (first == last).
- D2: Its longest edge: length in raw, its two endpoint indices and coordinates, and the next two longest edges. Count edges longer than 4096 raw.
- D3: Is this the SAME polygon as spool polygons the extractor emitted for one OSM way/relation? Find in `parser/osm_to_parcel_geometry.py` how background polygons are written to the spool (read, do not run the extractor) and report whether the ring's vertex order and the long edge are produced by the extractor's own code (cite the function and lines) or only by the build. If the spool carries an id, report it.
- D4: For the 10 disc fill pieces reported as failing in cell `(1726,162)` leaf `[1118]` (`background_boundary`, L0, see `k1_a.json` samples) and in cell `(1770,203)` leaf `[362]` (`background`), decode the cell's pieces with the Python decoder path used by `dbg1.py` and report per piece: type, class, vertex count, bounding box, the nearest spool shape of the same type (home cell, record, distance), and whether the cell's centre is inside that shape by even-odd and by winding.
- D5: For the 10 failing completeness cells in `k1_a.json` (L0: (1814,548), (1709,554), (1529,576), (1530,576), (851,637), (867,638), (869,638), (870,638), (871,638), (872,638)): which spool polygon of the stated type meets the cell (home cell, record, bbox), and what the disc holds in the cell for that type (piece count and bboxes).
- D6: For the 10 failing interior_cover samples: type, cell, the covering shape's piece class, and which spool shape (if any) contains the cell centre by even-odd and by winding.
- D7: name_anchor failure: decode the L0 leaf 928 of cell (0,541); report the name record (string, type), its raw position (0,370) and lat/lon; find the spool names in cell (0,541) and its 8 neighbours with distance to that point; report the nearest and whether any spool name has lon exactly 90.0 or lies in cell (-1,541) (west of the lattice edge). Report what the extractor does with names at lon 90.0 (cite the code).
- D8: For levels 2 and 6 samples (cell (449,77) L2 leaf [417] background and background_boundary; cell (453,76) L2 boundary; cell (27,9) L6 leaf [155,1] boundary): the same facts as D4.

## Changes

Scripts and outputs in `output/scratch-3-06/` only. Do not edit anything under `parser/`.

### Keep untouched

Everything in the repo.

## Done evidence

- `output/scratch-3-06/dossier.md` answers D1 to D8; every answer carries a command or script path and its numbers; unanswered ones are marked `unestablished` with the reason.
- A final section "Facts that could confuse the classification" listing, as observations only, anything that makes a question's answer depend on assumptions (for example the home cell of a tall shape).
- Report: the dossier path, the D1 identity line, the count of answered/unestablished questions.

## Report back

Under 1,500 tokens. Status: `done` | `done with concerns` | `blocked` | `needs context` | `over budget`. What changed, the check output before and after, any deviation and why, any contradiction with the cited contracts. Never resolve a contradiction silently. A non-trivial bug outside your evidence: symptom, location, root cause if found; do not fix it here.

Do not spawn agents beyond read-only research helpers. If this unit needs one, it was mis-sized: report `blocked` and say so.
