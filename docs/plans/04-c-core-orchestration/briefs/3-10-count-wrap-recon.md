# Brief: 3-10 — Count-wrap fix recon: how readers treat multiple background units of one class

Consumer: the orchestrator, who authors fix unit 3-11 (count-wrap fix in `_cenc.c:enc_bg`) from this unit's answers and `briefs/3-fix-template.md` (build-side C fix, recorded re-oracle, Assumption 1).
Owned paths: `output/scratch-3-10/` (git-ignored scripts/tables) and, on completion, `docs/plans/04-c-core-orchestration/triage/count_wrap_recon.md`. No code edits.
Commits: commit and push only `triage/count_wrap_recon.md` when done evidence passes.
Depends on: 3-08 (rule O06), `output/scratch-3-09m/mask_measure.md` (sister-mask measurement).
Runs alongside: nothing heavy; any heavy step under `flock output/.heavy.lock`, one at a time; no cbuild in this unit.
Tier: Sonnet 5.5 (RE-risky: on-disc format semantics). Mandatory independent review by another Sonnet 5.5 before 3-11 is authored.
Budget: no read cap; 80 tool turns. Past the budget stop and report `over budget` with the answered questions.

## Background (cited facts)

3-08 rule O06 (`build`, completeness): `parser/kiwiw/_cenc.c` `enc_bg` writes the per-class unit count as `(class_n[c] & 0xFFF) | (c << 14)` (line ~789) with no overflow check while writing ALL records; cells with more than 4095 records in one class wrap, so a decoder reading the declared count misses the rest. 3-09m measured 37 wrapping cells (41 frames) on `output/scratch-3-11/G/ALLDATA.KWI` (max 6415 records, physical − declared = 4096 in every one, each a single class-2 unit); 3-08 had audited only the 9 that carry failing completeness rows. The frame format: unit table of 4-byte entries `(0, count|class<<14)`, bits 11:0 count, bit 12 reserved, bit 13 height flag, bits 15:14 class; unit count `n_units` = number of non-empty classes (≤ 4) by construction (`n_in` sizing around L747, squeeze around L772). The proposed fix is to SPLIT a class with more than 4095 records into several units of at most 4095. That is unproven: it depends on how every consumer of the disc treats two units of the same class.

## Questions to answer (each with file:line or byte evidence, no inference stated as fact)

Q1. D1 / K1 / `parser/kiwiw` decoders and any Python decoder in `parser/` (find them: `grep` for the unit table walk): do they loop over `n_units` entries and accept the same class twice? Do they sum, or does a later unit overwrite? Show the loop code.
Q2. Is there any evidence of the real firmware / original-disc convention? Search `docs/` (format specs, `docs/design/`, `docs/provenance.md` third-party specs, archived vendor/disc analysis that is already in the repo or on disk under `output/` or the paths `docs/provenance.md` names) for: the unit-table layout, whether `n_units` may exceed one per class, and whether any ORIGINAL (vendor) disc cell has more than 4095 records in a class or two units of the same class (scan the original disc image listed in `docs/provenance.md`, offline, with fresh code). Report the count of original cells with duplicate-class units and the max records per class unit in the original.
Q3. The unit-table sizing in `enc_bg` (L740-790): `n_in` / `unit_off` / `rec0` capacity for `n_units` up to 4 + splits; does the frame header (`out[2..5]`, `esz`) and SUB_CAP leave room? Use the measured 974-byte worst-case headroom from 3-09m for bg frames; compute for each of the 37 cells the extra bytes needed (4 per extra unit) and whether any exceeds the headroom.
Q4. Which readers or tools compare ALLDATA bytes (goldens, `test_build_alldata.py`, `-j1 == -j12`, K1 `completeness` expectation of record counts): list what changes if the 37 cells change.
Q5. Alternative not requiring a format guess: could the 4096-record wrap instead be avoided by splitting at the SHAPE level (cell-local; two class-2 units are what the format already supports for height/other attributes?) or by not emitting some records? State for each option what the decoder sees. Do not recommend clipping (drops real geometry).
Q6. Verdict: for the 37 cells, state which of {split into multiple same-class units; other} is supported by Q1-Q5, which is unsupported or unknown, and what the last-mile risk is (firmware reading). If Q2 shows the original disc has no same-class duplicates and nothing proves the firmware accepts them, say so plainly: that is a format risk the orchestrator must put to Cody before 3-11.

## Done evidence

- `triage/count_wrap_recon.md` with Q1-Q6 answered, the table of the 37 cells (cell, level, declared, physical, extra units needed, headroom after), the scripts' paths in `output/scratch-3-10/`.
- One reproduction of the 9 known wrap cells from the 3-08 list by your own scan (cross-check).

## Report back

Under 600 tokens: status (`done` | `done with concerns` | `blocked` | `needs context` | `over budget`), Q6 verdict first, deviations. Never resolve a contradiction silently. Do not edit code or spawn agents.
