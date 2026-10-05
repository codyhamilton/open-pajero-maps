# Implementation — 14 completeness root cause

- Tool: OpenCode DeepSeek Flash (Phase 2); Phase 1 was Codex `gpt-6.1-sol`
- Session: Phase 2 refine + execute
- Started: 2026-10-05 ~23:05 Australia/Brisbane (Phase 1)
- Phase 1 closed: 2026-10-05 ~23:34 Australia/Brisbane
- Phase 2 refine: 2026-10-06 ~00:09 Australia/Brisbane

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

**Refine accepted (docs-only, Execute).** Approach C: R-presence primary + cell-local check; complete-repair package for R=0; residuals → open questions. Units `2-01`, `2-02`, `2-03` briefed under `briefs/`. `artifact_feedback` MCP unreachable — continued without workflow post.

Seed cross-tab from Phase 1 TSV (pre cell-local / pre repair):

| Bucket | R>0 G=0 | R=0 G=0 |
| --- | ---: | ---: |
| historic_188 | 1 | 187 |
| added_89 | 0 | 89 |
| neither_499 | 342 | 157 |
| **total** | **343** | **433** (incl. row 335 source gap) |

Execute units via OpenCode DeepSeek Flash next; Phase 2 close trailer only on the closing commit.
