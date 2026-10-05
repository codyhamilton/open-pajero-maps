# Implementation — 14 completeness root cause

- Tool: Phase 1 Codex `gpt-6.1-sol`; Phase 2 units 2-01 OpenCode DeepSeek Flash, 2-02/2-03/close Execute background worker (CHM reseated the assigned instance to Codex at 01:35 for any new seats)
- Session: Phase 2 refine + execute
- Started: 2026-10-05 ~23:05 Australia/Brisbane (Phase 1)
- Phase 1 closed: 2026-10-05 ~23:34 Australia/Brisbane
- Phase 2 refine: 2026-10-06 ~00:09 Australia/Brisbane
- Phase 2 closed: 2026-10-06 ~02:30 Australia/Brisbane

## Phase 1 — Per-row completeness evidence table

**Closed.**

### Disc restore (Execute)

- No local file matched sha `4ed9cd80…` at start (scratch-3-11/G_new remains protected `013586b5…`; `output/ALLDATA.KWI` was `51c254ac…`).
- Fresh full-AU encode under `flock output/.heavy.lock` from main checkout:
  - spool `output/extract_timing/spool` → `output/scratch-14/G_new/ALLDATA.KWI`, `-j4`
  - log `output/scratch-14/full_build.log` (encode 119.0s, assemble 13.5s)
- Result sha256 `4ed9cd801bdd70992a9b7bd090803ffae349515f87546f044b21157e68e99d72` — **matched** prior oracle; size 1,692,105,152. No new oracle.
- Protected `output/scratch-3-11/G_new/ALLDATA.KWI` unchanged.

### Evidence (Codex `gpt-6.1-sol`, pid ~2108761, worktree `open-pajero-maps-14-completeness`)

- Brief: `briefs/1-01-evidence-table.md`
- Fresh K1 completeness-only dump under flock, `-j6`: **776** failing identities (drift vs 3-17 failing: **0**).
- Committed table: `triage/completeness_evidence.tsv` (776 rows) + `triage/completeness_evidence.md`
- Flags: all **188** historic and **89** added present and disjoint; **499** in neither.
- Classify: exit 2 — missing `other_mechanism` (sides cleaned). Assignment column = `evidence-gap:other_mechanism` for all 776. Header states verified attributed-by-rule **0** in this table; historical 3-17 partition (468/308) and 3-15 (274) retained as inputs, not substituted. Numeric difference of unresolved evidence entries vs 3-17 unclassified: **+468**; vs 3-15: **+502** (measures missing assignment evidence, not partition movement).
- R/G/spool witnesses under `output/scratch-14/witnesses/` (git-ignored); audit PASS (1,791 byte ranges). One spool source-evidence gap (native row 335).
- Provenance scratch entry for `output/scratch-14/` committed.
- No rule/encoder/checker edits; 3-16/3-17/170 untouched. Plan 04 Phase 3 not claimed closed.

### Carried

- Live O01/O04/O05/O06 partition blocked until `other_mechanism` sides are recovered or recomputed reproducibly (Phase 2 refine rejected blocking on recovery; may try as optional discriminator only).
- One spool source-evidence gap at `(0,1379,1138,288,…)` — which source/requirement branch establishes the K1 demand?
- Assignment-gap numeric deltas (+468 / +502) are not live unattributed drift; do not treat them as count movement in Phase 2.
- Phase 1 R presence is frame-presence (sparse-tile alias possible); Phase 2 unit 2-01 must apply cell-local geometric meet before closing `g-omits-cell-local-dvd-type`.

## Phase 2 — Root-cause groups

**Closed.** Exhaustive, disjoint union map `triage/phase2_membership.tsv` (776):

| Unit | Commit | Group / ledger | Rows | Reproducer |
| --- | --- | --- | ---: | --- |
| 2-01 | `b775e9b` | `g-omits-cell-local-dvd-type` | 342 | `triage/cell_local_2-01.py` |
| 2-02 | `bcb266b` | `r-absent-complete-repair-zero` | 432 | `triage/complete_repair_2-02.py` (EO faces + densified `emit_piece` mirror + production C `bg_shape` probe; 0 emits / 0 C records on 432/432) |
| 2-03 | `e24b89b` | open questions `Q-source-335`, `Q-tile-alias` (765) | 2 | `triage/residuals_2-03.py` |

Predicted Phase 3 movement: up to −342 (2-01, build or checker; Phase 3 picks) and
−432 (2-02, proven non-deviation or checker stops the demand). The 2 open questions
stay open. Production C confirms 2-01 sources give 0 records on 342/342 (densify
caveat closed). Plan heavy guards were used throughout: `run_heavy_python.py`
(flock + memory.peak logs in `output/scratch-14/runs/`), windowed/`--max-seeds`
probes before `--all-seeds`.

**Spool incident (2-02 setup, 00:44).** The live `output/extract_timing/spool` was
destroyed by a symlink step that resolved through the worktree's `output` link.

- Restored with extractor tree `34a04cc`. A tip-extractor rebuild was rejected
  because 138/775 witness cells differed.
- Proofs: 775/775 witness pins match, and a full-AU `-j4` re-encode at `f385ef5`
  gives `4ed9cd80…` (byte-identical).
- Record: `output/scratch-14/spool_recovery/INCIDENT.md` and `docs/provenance.md`.

### Carried to Phase 3

- **Q-source-335.** No spool source reproduces the K1 demand within ±32 cells.
  Instrument the checker read-only to name the demanding shape.
- **Q-tile-alias (765).** The evidence matches the 2-02 mechanism. Design should
  rule whether cell-local R absence counts as `R_polygon_count == 0`.
- **Locus choice.** Phase 3 decides the 2-01 locus (build vs checker) and the 2-02
  disposition (non-deviation vs checker).
- Plan 04 Phase 3 is **not** closed by this plan.

### Phase 2 refine (record)

**Refine accepted (docs-only, Execute).** Approach C: R-presence primary + cell-local check; complete-repair package for R=0; residuals → open questions. Units `2-01`, `2-02`, `2-03` briefed under `briefs/`. `artifact_feedback` MCP unreachable — continued without workflow post.

Seed cross-tab from Phase 1 TSV (pre cell-local / pre repair):

| Bucket | R>0 G=0 | R=0 G=0 |
| --- | ---: | ---: |
| historic_188 | 1 | 187 |
| added_89 | 0 | 89 |
| neither_499 | 342 | 157 |
| **total** | **343** | **433** (incl. row 335 source gap) |

