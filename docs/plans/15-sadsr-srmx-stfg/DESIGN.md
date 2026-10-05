---
design_id:
---

# SADSR SRMX STFG vs R

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Maps Manager asked Design for the next design after plan 14, runnable without the missing completeness disc/dumps. Close one concrete schema unknown: SADSR SRMX street STFG, where G writes `0x3f00` (NAME absent) under a false "matches the real disc" claim while committed R evidence is `0x7f00` (bits 0–6 including NAME). Land each phase on master. No feature branch. No pull request. Do not reseat 170, 3-16, or 3-17. Do not draw plan 04 phases 4–6 or plan 06. Do not invent Phase 3 close.

## Problem

`docs/schema/flags.md` row "SADSR SRMX street STFG value" is still **unknown**. Committed facts already disagree with the generator:

| Surface | What it says | Status on master |
| --- | --- | --- |
| `docs/schema/index-idx.md` STFG / SRMX rows | R SADSR201 SRMX is `7f00` on 38,119 of 38,120; SADSR202 all 2,827 are `7f00`; gated fields after STFG are STID…NAME (bit 6 = NAME) | **verified** |
| `parser/kiwiw/search_frame.py` | `STFG=7f 00` → the 7 fields STID..NAME present | code comment aligned with schema |
| `parser/osm_to_address_index.py` `street_to_srmx_dict` | Emits STFG `0x3f00` (bits 0–5 only; no NAME key); docstring claims this "matches the real disc's `STFG = 0x3F 0x00`" | **false claim**; conflicts with verified R |
| `parser/tests/test_address_extractor.py` `test_stfg_bits_correct_for_srmx` | Asserts `STFG[0] == 0x3F` | locks in the wrong pattern |
| `parser/kiwiw/index_data.py` SRMX walk comment | Says always `7f 00` with "7 fields" then lists six names and "NAME absent" | internally inconsistent; must not be treated as R truth |

This is a processing defect (G omits a field R carries), not a natural OSM shortfall. Plan 14 owns completeness unattributed rows and is blocked on the missing disc; this slice does not need that disc or those dumps.

Verified on `origin/master` at `4f8a03d` from committed files only — no live IDX mount was present in the design environment. Plans **01–05** and **07–14** occupy those numbers; **06** is not a work unit on master (unsigned CI-gate draft only). This plan is **15**.

## Solution shape

Prove from master evidence that R's SRMX STFG pattern is `0x7f00` with NAME present, that G's `0x3f00` claim is false, then make G emit the verified pattern with a NAME field and update the schema unknown to verified. No full WP3 program; no other IDX families.

### Domain: R STFG evidence

- Owns: the proof package that closes the flags.md unknown for this row, citing only committed schema/code/tests (and optional remounted-IDX confirmation if present, never required).
- Contract: a committed evidence note under this plan folder states: (1) R SRMX STFG high-confidence pattern is `0x7f00` with bit 6 = NAME present, with citations to `index-idx.md` verified rows and `search_frame.py`; (2) G's "matches real disc `0x3F00`" sentence is false; (3) `index_data.py`'s "NAME absent" gloss of `7f00` is inconsistent with the seven-field bit layout and is not R truth. No encoder edit in this domain.
- Non-goals: no DB0/JG0/… suffix work; no POISR/ITSSR bodies; no completeness classify; no disc re-encode of ALLDATA.

### Domain: G SRMX emission

- Owns: `street_to_srmx_dict` (and any assembler path that trusts its STFG/NAME shape) so generated SRMX records carry STFG `0x7f00` and a NAME field.
- Contract: every SRMX dict produced for a street has `STFG == [0x7f, 0x00]` (or equivalent bytes) and a `NAME` string; synthetic unit tests assert that shape and fail on `0x3f00` without NAME. Round-trip tests that skip without a mounted IDX stay skip-tolerant; they are not the close gate.
- Non-goals: no change to SRT1 `0x07` or SRHA STFG patterns already marked verified; no regeneration of all 99 IDX files as a program milestone; no claim that WP3 is started or finished.

## Decisions

1. Plan number is **15**. Plans 11–14 are on master; 06 is not used.
2. Land on master directly. No feature branch. No pull request.
3. Two phases, one coding worker each. Refine skipped (approaches known).
4. Bound to SADSR SRMX street STFG + NAME only — one UNKNOWNS slice, not a census of 94 unknowns.
5. Do not reseat design 170, unit 3-16, or 3-17. Do not draw plan 04 phases 4–6 or plan 06. Do not write 3-90 or claim Phase 3 closed.
6. Verify every claim against files on master (void plan-10 lesson). Do not invent R NAME-vs-KYCH equality from a commit message; ledger it.
7. Assigned instance for this lane's workers is Codex (Design does not start workers).

## Assumption ledger

### Assumption 1

- Question: can this plan close without remounting R or the missing completeness disc/dumps?
- Answer chosen: yes. R's `0x7f00` / NAME-present pattern is already **verified** on master in `index-idx.md` and reinforced by `search_frame.py`. Phase outcomes use synthetic tests plus schema updates. Optional remounted-IDX spot-check is bonus, not a gate.
- Rationale: plan 14 Phase 1 is blocked on disc `4ed9cd80…`; this slice must stay runnable while that waits.
- If wrong: Cody restores an IDX mount; Phase 2 may add a non-blocking confirm that sampled SRMX STFG bytes are `7f00` with NAME decodeable — still no completeness dumps.

### Assumption 2

- Question: what string does G write into SRMX NAME when bit 6 is set?
- Answer chosen: the same street string already used for KYCH (`street.name`), unless committed evidence on master already distinguishes NAME from KYCH for SADSR SRMX.
- Rationale: no checked-in per-record NAME≠KYCH sample was found at design time; KYCH is the search key and NAME is the next gated field on the verified SRMX field list. Emitting the street name is the minimal processing that restores the presence bit R uses.
- If wrong: Cody supplies a NAME rule (e.g. display vs folded key); Phase 2 adjusts the NAME value only, STFG stays `0x7f00`.

### Assumption 3

- Question: does fixing SRMX STFG imply starting WP3 as a package?
- Answer chosen: no. This is a bounded schema-unknown / G-defect close on one already-written helper. OVERVIEW's WP3 "Not started" row is not opened as a program.
- Rationale: OVERVIEW forbids inventing packages from partial work; the standing rule still requires unexplained G≠R claims to be fixed when evidence exists.
- If wrong: Cody widens to a WP3 design; do not silently absorb POISR/ITSSR into these phases.

### Assumption 4

- Question: may Phase 1 edit encoder code?
- Answer chosen: no. Phase 1 is evidence + schema/comment honesty only. Phase 2 owns the emission fix and the test that today asserts `0x3F`.
- Rationale: keep the false-claim proof separable from the behaviour change so review can reject one without the other.
- If wrong: Cody allows a single phase that both proves and fixes; still land on master as one worker.

## Open questions

1. On remounted R, is SRMX NAME byte-identical to KYCH for the dominant `7f00` population, or a distinct display form? **Not a Phase gate.** Answer when an IDX is available; if distinct, a follow-up adjusts NAME only.
2. The single SADSR201 SRMX row that is not `7f00` (1 of 38,120) — what is its STFG and is it in scope? **Out of scope** unless Phase 1 finds a committed identity; otherwise leave as a named residual in the evidence note.

## Phases

### Phase 1 — Prove G's `0x3f00` claim false; close the unknown as documented conflict

- Outcome: a committed evidence note under `docs/plans/15-sadsr-srmx-stfg/` cites the verified `index-idx.md` STFG/SRMX rows and `search_frame.py`'s `7f00` → STID..NAME reading, quotes the false `osm_to_address_index.py` "matches the real disc" sentence, and records that `index_data.py`'s "NAME absent" gloss of `7f00` is inconsistent with a seven-bit presence mask. `docs/schema/flags.md` SRMX STFG row is updated from **unknown** to a status that names the conflict resolved-as-defect (G wrong; R `0x7f00`+NAME stands), with Evidence pointing at the note. `UNKNOWNS.md` is regenerated by the existing lint tool so the row leaves the unknown census. No change to `street_to_srmx_dict` behaviour yet. No ALLDATA/completeness work. Disc sha unchanged.
- Surfaces: `docs/plans/15-sadsr-srmx-stfg/` (evidence note), `docs/schema/flags.md` (and index-idx cross-links if a one-line clarity fix is needed), `docs/schema/UNKNOWNS.md` via `parser/tools/lint_schema.py --write`; optional comment-only honesty fix in `parser/kiwiw/index_data.py` if required to stop teaching "NAME absent" for `7f00`.
- Approach: known
- Depends on: master tip containing the verified schema rows (present at `4f8a03d`).
- Refine: skipped. One worker.

### Phase 2 — G emits SRMX STFG `0x7f00` with NAME

- Outcome: `street_to_srmx_dict` returns STFG bytes `0x7f00` and a `NAME` field (Assumption 2). `test_stfg_bits_correct_for_srmx` (and any sibling asserting `0x3F`) expects `0x7F` and asserts `NAME` is present and equals the chosen string rule. A synthetic write/parse smoke (existing index writer/search_frame helpers, no mounted disc required) round-trips one SRMX record with bit 6 set. The false "matches the real disc's `0x3F00`" docstring is removed or corrected. Schema Evidence/Code columns for the flags.md row cite the new tests. Disc sha for ALLDATA is unchanged (IDX-only helper). Plan 04 Phase 3 is not marked closed.
- Surfaces: `parser/osm_to_address_index.py`, `parser/tests/test_address_extractor.py` (and a small writer/parse test if one is needed beside it), schema rows touched in Phase 1 if Code column must move.
- Approach: known
- Depends on: Phase 1 evidence note and schema status update.
- Refine: skipped. One worker.

## Provenance

- Ground tip read: `origin/master` `4f8a03d8c157d73da314b2613f6bba2dfaa4835f` (“docs: add plan 14 completeness root-cause design”).
- Candidate chosen from plan 14 `NOTES.md` item 8 / pool item 5 (schema UNKNOWNS), bounded to the SADSR SRMX STFG conflict in `flags.md:148` — drawable without disc `4ed9cd80…` or completeness dumps.
- Rejected for this design (one line each): O03 pin formalization (already attributed spool; bookkeeping only); R01 exclusivity (needs dumps beyond L0/291); word-7 residual 28 (parcel IDs not on master; needs R); IDX DB0/JG0/… suffixes (needs R headers); envelope/trim (acceptance criteria not on master; still pending); region polygon 65623 (needs missing completeness dumps).
- Inputs cited, not reseated: `docs/schema/{flags.md,index-idx.md,UNKNOWNS.md}`, `parser/osm_to_address_index.py`, `parser/kiwiw/{search_frame.py,index_data.py}`, `parser/tests/test_address_extractor.py`, `docs/plans/14-completeness-root-cause/`, `docs/OVERVIEW.md`.
- Draft format followed: `/workspace/maps-design-drafts/14-completeness-root-cause/DESIGN.md` and plan 09.
- Design method: workflow design skill structure (problem, solution shape, boundaries, contracts, phases closed by provable outcomes, headless assumption ledger). Workflow-service posts skipped under the user instruction.
- Plan 04 Phase 3 stays open. Plan 14 stays blocked on disc. This plan does not draw phases 4–6 or plan 06.
