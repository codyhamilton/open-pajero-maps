# Brief: 3-11 — Fix O06: `enc_bg` class record count wraps at 4096; split into same-class units

Consumer: the orchestrator (records the re-oracle, requests the Sonnet 5.5 review of the cell list) and Cody (signs the re-oracle at phase close).
Owned paths: `parser/kiwiw/_cenc.c` (`enc_bg` only), the matching test(s) under `parser/tests/`, `output/scratch-3-11/` (git-ignored scratch; the G build `output/scratch-3-11/G/ALLDATA.KWI` is the OLD oracle: never delete or overwrite it), and on completion the golden `output/goldens-3C/l0_divided_trim_halo` only if the pre-edit check confirms it holds a wrap cell.
Commits: commit and push code + tests + the unit's record only; never stage discs or dumps. Every new untracked material gets a `docs/provenance.md` entry in the same commit.
Depends on: 3-08 (rule O06), 3-10 (`triage/count_wrap_recon.md`, reviewed ACCEPT in `triage/review_3-10.md`), `output/scratch-3-09m/mask_measure.md`.
Runs alongside: nothing. Serial (touches `parser/kiwiw/`). Heavy runs under `flock output/.heavy.lock`, one at a time; `cbuild`/make at most `-j4`; harness/K1 at most `-j6`; never two heavy jobs at once; do not drop caches. Do not touch `output/scratch-2-07/` or `output/scratch-3-06/`.
Tier: Flash executor (Sol if Flash fails once), RE-risky; mandatory Sonnet 5.5 review of the diff AND the cell list before it is treated as landed.
Budget: no more than 60 tool turns for the edit and tests; the heavy steps (A, D) are one command each, and a heavy run of about ten minutes or more is kicked off here and verified by a fresh unit (3-12).

## Cited facts (copy, do not re-derive)

- Rule O06 (`triage/rules_other.json`, cause `build`, kind `completeness`): `enc_bg` writes the per-class record count as `(class_n[c] & 0xFFF) | (c << 14)` (`_cenc.c` ~L781-789) while writing ALL records, so a class with at least 4096 records declares count − 4096 per wrap. Unit-table entry layout: 4 bytes `(0, count | class<<14)`, bits 11:0 count, bit 12 reserved (must stay 0), bit 13 height flag, bits 15:14 class. `n_units` = number of non-empty classes (at most 4) by construction; sizing `n_in` around L747, squeeze around L772, header loop L784-790.
- Scope (3-09m, 3-10): 37 cells / 41 frames on the G build, all level 0, each a single class-2 unit, physical − declared = 4096 in every one, max physical 6,415. Each needs exactly one extra unit (+4 B). Cell list: `triage/count_wrap_recon.md` (37-cell table). Sister masks (`_cenc.c` ~L222, L241, L459, L460) are not reached (tightest L460, 1,997 of 2,047): do not edit.
- Readers (3-10 Q1): D1 `_d1.c` L205-262, `background.py`, `kiwiread` `dumpbkgd` loop over all units, take each unit's own count, and SUM same-class units; the offset word is ignored. K1 reads D1's flattened tables, so it sees the sum.
- Original disc (3-10 Q2): 57,693 elements have 2-4 same-class units, type-code-disjoint; max class unit 517 records; none at 4,095. A split by type code is impossible here (one type code has up to 6,401 records), so the split is by record count: same class, same type codes across the units. That has no original-disc precedent and no firmware evidence. It is a KNOWN, Cody-accepted format risk (O06 path locked by Cody/BTM); last-mile verification is in the vehicle. Do not clip records and do not use reserved bit 12.
- Offset word: G writes 0, R writes the true offset in every element. That is a separate, pre-existing difference for all ~1.4 M bg elements. Keep writing 0 here (changing it moves every bg frame, a far larger re-oracle); do NOT fix it in this unit. Record it as Carried for Cody.

## The change

In `enc_bg`, for each class with `class_n[c]` > 4095, emit `ceil(class_n[c] / 4095)` consecutive units of that class: all but the last with count 4095 (or any fixed rule giving every unit at most 4095), the last with the remainder. The records stay physically in the same order they have today (the unit boundary is the only change, so the physical record bytes do not move). Size `n_in` / `unit_off` / `rec0` for the maximum (up to 4 classes with splits), keep the squeeze correct, and keep header `esz` / `out[2..5]` derived from `p` so +4 B per extra unit flows through. The change must be byte-identical for every element with no class above 4095 records. If a frame would exceed the 131,070 ceiling or SUB_CAP, stop and report `blocked` (never clip).

## Pre-edit checks (record each result; any failure is a stop, report `blocked`)

C1. Whole-frame headroom of ALL 37 cells (3-10 finding 7): for each of the 37 cells sum every sub-frame of the whole map frame from the G build (do not use the scan's `frame_end`), and confirm whole frame + 4 ≤ 131,070. Golden cell (1755,591) is 131,060 B (6 B left); riskiest others (1681,729), (1929,1121), (1530,844).
C2. Perth: confirm by an actual scan of the Perth fixture disc that none of the 41 elements lies in it (bbox arithmetic says ix 816-848, iy 840-864 vs the 37 cells at ix ≥ 872); the Perth sha `da13a775…` must not move.
C3. Goldens: list the window of every golden under `output/goldens-3C/` and `docs/provenance.md`, and name exactly which contain a wrap cell (known: `l0_divided_trim_halo`, window 1755 591 1756 592).
C4. Capture the OLD oracle before editing: full-AU sha (87a01b14…), Perth sha, and the cell-by-cell inventory of the G build (path, sha256 in the record). Keep the old disc.

## Steps (in order)

A. `cbuild` (-j4) then build the full-AU disc and the Perth disc with the fix, each under `flock output/.heavy.lock`.
B. Cell-by-cell compare old vs new full-AU: the differing cells must be EXACTLY the 41 elements in the 37 cells (counts per level: 37 cells, all level 0). Any extra differing cell is a stop: report `blocked`.
C. Perth sha unchanged (da13a775…), else `blocked`.
D. Re-run K1 on the new full-AU disc (heavy, under the lock, `-j6`, dump-off wall must stay ≤ 72 s) and re-classify with `k1_triage.py classify`: rule O06 rows go 13 → 0; every other rule's rows unchanged except as the completeness `physical` expectation moves (quote before/after per rule; explain any other delta by cause, never accept it unexplained).
E. Tests: a new unit test in `parser/tests/` that encodes a synthetic background cell with 6,415 class-2 records and asserts (i) two class-2 units with counts 4095 and 2320, (ii) D1 decodes all 6,415 records, (iii) a cell with exactly 4095 and one with 4096 records, (iv) a cell with fewer than 4096 is byte-identical to HEAD output. Run the existing suite; `-j 1` == `-j 12` byte-equal; H-budget tests; full-AU assembly time stays under about 1 min (name the cause of any regression).
F. Re-capture only the affected goldens named by C3; the unaffected ones must stay byte-identical.

## Done evidence

Recorded in `IMPLEMENTATION.md` under the 3-11 heading: C1-C4 results; old and new full-AU shas; Perth sha (unchanged); the EXACT differing-cell list (path to the TSV in scratch plus counts per level) equal to the 41 predicted; golden names re-captured; K1 before/after counts per rule (O06 = 0); wall times (K1 dump-off, assembly); the sha256 of the old oracle disc kept. The Sonnet 5.5 review of the diff and of the cell list is a separate step by the orchestrator.

## Report back

Under 600 tokens: status (`done` | `done with concerns` | `blocked` | `needs context` | `over budget`), the old/new shas, the differing-cell count first, deviations. Never resolve a contradiction silently. Do not spawn agents. Do not run `-j` above the caps. Do not start Phase 4; do not add a `Workflow-Phase` trailer.
