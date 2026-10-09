---
design_id:
---

# R-G5-6: G emits byte-identical same-type background duplicates that R never holds — derive R's rule from R, dedup in the encoder, successor oracle

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Cody's hard bar as restated 2026-10-08: every deviation needs a proven root cause; no waivers; carried is not closed; never pick an arbitrary rule and call it proven.

Cody standing rule (2026-10-09): Maps Execute cleans its scratch after every phase, keeping only what the ledger or the next phase needs. A phase isn't done until its scratch is cleared.

Design brief (2026-10-09): draft plan 68 for new row R-G5-6 (plan 63). Establish what R does where G has duplicates (one copy at the same emission position — first or last block — merged, or absent), from per-leaf R-vs-G comparison on a committed sample with a hash-fixed holdout. State what a dedup must preserve (record order, kept neighbour pieces, counts / offsets / leaf sizes), where it goes in the encoder, and the successor-oracle gates (leaves with duplicates → 0 and R-matching where R covers; no regression in other residual counts; Perth and AU). Memory peak in the 56 ledger; scratch receipts. Same-type-but-different-bytes cases are a separate class with their own RC.

Master direct. Heavy work under flock + `run_heavy_python.py --memory-max 12G`, encode `-j4`, K1 ≤ `-j6`. Oracle change only through the successor-oracle discipline (plans 48 / 50 / 53) and a Design accept. **Out of scope and untouched:** F6 catch-all→288 / kind-order (R-G9-3-a), roads preference, L8 expansion (Cody). No plan 04 P4–6, no 3-90. Assigned Execute instance: per CHM seat.

## Problem

**Ground (GitHub `origin/master` `61d2fe8`, plan 63 close-out, read-only on the box, 2026-10-09):**

1. **The row.** `residuals.tsv` R-G5-6 (owner Design, `blocks-phase3`, "Design may reclassify"): G emits byte-identical same-type class>0 background records in one leaf; R never does. Mechanism (plan 63, proven on 1,083 sampled duplicate classes): each routed same-type source emits its own clip piece, and E2 does not deduplicate identical pieces from distinct sources (`33006aa` `_cenc.c` `enc_bg` / `_e2.c` `e2_merge`). Not fixed by plan 63.
2. **The census** (`p7_producer_tie/dup_census.py`; distinct leaf frames, alias slots read once; class>0 only):

   | Disc | Leaves (distinct frames) | Leaves with dups | Dup classes | Extra copies | Notes |
   | --- | ---: | ---: | ---: | ---: | --- |
   | R `8c2d2027…` | 482,473 (+3,469,500 L0 alias slots) | **0** | 0 | 0 | R L0: 235,371 distinct frames |
   | `013586b5` | 3,954,156 | 336,329 | 338,760 | 445,137 | L0 336,325; L2 4 |
   | live `0c22b266` | 3,954,165 | 336,135 | 338,565 | 444,934 | L0 336,132; L2 3 |

   - On live, **338,038 of 338,565 dup classes (99.8%) are L0 type 288**, the L0 catch-all (plan 51; `bg_type.json` `match{}→288`). Then 291: 364; 321: 110; 289: 17; 290: 12 (+6 at L2); 578: 10; 322: 5; 640: 3.
   - R holds 2,203,680 type-288 records at L0 (plan 51) and none of them is duplicated in a leaf.
3. **The emission order is proven.** Plan 63's accepted rule (537/537 derivation, 546/546 holdout): copies in leaf order follow (source class, own cell first, then source (iy, ix), then ri) — `enc_bg` class-major, merged background ordinal, each background's `bg_shape` pieces contiguous, over `kw_e2` / `e2_merge` (own backgrounds first, then E1-routed items by target, source (iy, ix), shape). Divided leaves follow `dv_bg_cells` / `dv_probe`.
4. **What R does with the same geometry is unmeasured.** Plan 63 measured only that R has 0 duplicates. Whether R keeps one copy (and which block it sits in), merges the two sources' pieces into one record, or has nothing there, is not known. R's L0 is framed differently (235,371 distinct frames + aliases vs G's 3,707,037), so a byte-level comparison only works where the leaf framing is equal.
5. **Encoder at tip.** `parser/kiwiw/_cenc.c` `enc_bg` (L1182) writes records class by class through `bg_shape` (L1068) into a sub-frame (`SUB_CAP` 0x20000); a class above 4,095 records is split into several units (12-bit count). `_e2.c` `e2_merge` (L304) concatenates own + routed items; divided leaves size their cells through `dv_probe` (L746), and `dv_shrink` (L988) trims by size. Last encoder change: plan 53 (`afce673`).
6. **R-G5-4-a-1 overlaps this row.** Its 222 rows / 8 groups are byte-identical duplicate pairs (two same-type rings each emit the piece), decide builds under either candidate, and plan 63 left it with a note only (Task 2 of the brief; see "R-G5-4-a-1" below).
7. **Same-type, different bytes is not counted anywhere.** `dup_census.py` groups by (type, record bytes). Two same-type records from distinct sources whose geometry is equal up to start vertex or direction, or where one piece contains or overlaps the other, are invisible to it. Class-0 records are excluded too.

**R-G5-4-a-1 check (brief Task 2).** Plan 63's record says: "R-G5-4-a-1: a note only, because applying the rule there is a 63 non-goal (plan-62 consumer)"; `residuals.tsv` R-G5-4-a-1 stays `blocks-phase3`, owner "Design → plan 63". **Not discharged.** What is owed: a sidecar-proven producer for every copy and the decide verdict under it, for all 8 groups. Plan 63's committed `provenance.tsv.gz` already names both copies for leaf (1176,1591)[1784] shapes 1 / 3 (2 groups, 44 rows; window `t_0_1176_1591`). Leaves (1664,560)[1536], (1694,1781)[1726] and (1759,1513)[1343] (6 groups, 178 rows) have no window build. This plan's Phase 1 discharges it.

## Solution shape

### Domain: R-side truth for every duplicate class (census + committed sample)

- **Owns:** `triage/historical_bg/p10_bg_dedup/` (new): national tables on live `0c22b266` and R, a committed stratified sample, and the R-correspondence classification.
- **Contract:**
  1. **National census on live and Perth** (reuse `dup_census.py`; record per dup class: level, cell, leaf path, type, copies, record sha, and per copy its emitter by plan 63's rule).
  2. **R correspondence per sampled dup class**, classes defined before scoring:
     - **R-one-byte:** R's leaf for the same cell, with the same framing (same leaf path and frame bounds), holds exactly one byte-equal record;
     - **R-one-geom:** R holds exactly one same-type record whose decoded geometry in parent-raw equals the piece, framing differs;
     - **R-merged:** R holds a same-type record that contains the piece and also covers geometry G emits as a different (non-duplicate) piece from one of the two sources;
     - **R-absent:** no R same-type record within 1 parent-raw of the piece;
     - **R-noncomparable:** R's cell is an alias frame, or R's records there are of another type set (the F6 question for type 288). Counted and named, never a pass.
  3. **Position (R-one-byte and R-one-geom):** align G's and R's record sequences in the leaf on byte-equal (or geometry-equal) non-duplicate records. Record whether R's single copy sits in the block of the **first** emitter, the **last** emitter, or neither, per plan 63's emitter order.
  4. **Sample:** strata (level, type, copies, depth / divided, framing-equal or not), at least 60 classes per stratum where the stratum has them, picked by lowest `sha256("p68-sample:{level},{ix},{iy},{path},{sha}")`. Derivation / holdout split by the parity of `sha256("p68-holdout:…")[0]`. Sample, split and class definitions are committed **before** any R read.
  5. **National R counts** for the classes in item 2 over every framing-equal dup class, after the sample result is accepted (confirms the sample is not the whole story).
- **Non-goals:** any encoder change; F6.

### Domain: same-type, different-bytes pairs (separate class, own RC)

- **Owns:** a census of same-type class>0 record pairs in one leaf, on live G and on R, that are not byte-identical but are:
  - **D-rot:** the same ring up to start vertex and / or direction;
  - **D-contain:** one piece's geometry contains the other's;
  - **D-overlap:** pieces share area above a threshold committed before measuring.
- **Contract:**
  1. Counts on R and G per class and type; R's count is the parity reference.
  2. If G's count exceeds R's for a class, that class is a deviation with its own RC, proven the same way as the byte class: sidecar emitters on a hash-fixed sample, mechanism named in code, R correspondence. It does **not** inherit the byte-duplicate rule.
  3. A D-class whose RC is proven and whose fix is confined to the same encoder site may ride the same successor oracle. Otherwise it becomes an exact child row with its proven RC and its own plan. Class-0 same-type repeats are counted the same way.
- **Non-goals:** treating D-classes as byte duplicates; F6.

### Domain: dedup rule and what it must preserve

- **Owns:** the accepted dedup rule, scored against the R correspondence, and the preservation contract.
- **Contract:**
  1. **Candidate rules (defined before scoring):** keep-first (first emitter's copy), keep-last, keep-own-cell-first, merge-sources (one record from the union of the sources' pieces), drop-all. Accepted only at 100% on derivation **and** holdout over R-one-byte + R-one-geom classes, with a code path. R-merged and R-absent counts decide whether merge-sources or drop-all must be added; if R shows more than one behaviour, the rule must say which condition selects which, proven the same way.
  2. **Preservation (checked by tests and window gates):**
     - record order of every non-dropped record unchanged;
     - every neighbour piece kept, including the other pieces of the dropped copy's source (only the byte-identical record is dropped, not its source's block);
     - unit table: class counts reduced exactly by the dropped records; a class that falls to ≤ 4,095 rejoins one unit; a class emptied is squeezed out as today;
     - record offsets and sub-frame size recomputed from the written bytes, never patched;
     - divided leaves: `dv_probe` sizes come from the same dedup'd emission, so `dv_shrink` and division decisions see the real size;
     - leaf frame sizes, block / blockset sizes and frame addresses follow from the encoder; no hand-edited disc.
  3. **Knock-on effects are measured, not assumed:** leaf sizes; changes in division topology (2×2 / 4×4) and in `dv_shrink` trim decisions (e.g. roads that were dropped to make room for duplicate 288 may now be kept). Each changed decision is listed and compared with R's division and content for that cell.
- **Non-goals:** changing which sources emit (that is selection / F6).

### Domain: encoder site, successor oracle, residual

- **Owns:** the `_cenc.c` / `_e2.c` change with unit tests; the successor oracle; `residuals.tsv` R-G5-6 and R-G5-4-a-1.
- **Contract:**
  1. **Site.** Candidates: (a) `enc_bg`, after `bg_shape` writes a record, drop it when a byte-equal same-class same-type record is already in this leaf (per-leaf hash set); (b) `e2_merge`, drop routed items whose clipped piece will equal an existing one; (c) the divided-leaf path through `dv_probe`. Byte identity is defined on the emitted record, so (a) is the default. Refine picks the site with a test showing probe sizes and final emission agree.
  2. **Window gates** (output-neutral control first, then the change) on the committed sample's cells: non-duplicate leaves byte-identical to `0c22b266`; duplicate leaves equal to the accepted rule's prediction; K1 on windows failing 0.
  3. **Successor oracle (full AU `-j4`, and Perth), all required:**
     - **duplicates:** `dup_census.py` on the successor reports **0** leaves with byte-identical same-type class>0 duplicates at every level, AU and Perth;
     - **R match where R covers:** every R-one-byte / R-one-geom class nationally (not only the sample) has its surviving copy at R's position; R-merged / R-absent classes follow the accepted rule's branch;
     - **confined diff vs `0c22b266…`:** every changed leaf is a duplicate leaf, or a knock-on traced to one (same cell or its division / shrink), listed;
     - **R-DVD no-worse** (plan 48 precedent) on every changed cell: same-type coverage, road kept count, division topology;
     - **no regression in other residual counts**, each re-stated on the successor: `l0_degen` edge census (plan 53 predicate, and plan 67's if landed); L8 (7,4) dc12 pieces; (1755,591) sub (2,1) road count (R-G9-3-a — recorded, no F6 decision); harness `count_ratio` per level; K1 failing 0; representability; D-class counts not up;
     - Perth successor vs `5b86d33e…` with the same gates;
     - determinism `-j1` == `-j4`; close gates a/b/c (tests; AU wall median of 3 at `-j4` vs 29.33 s; sha).

     Design accepts before promotion; OVERVIEW oracle line and the oracle-chain pin move.
  4. **Residuals:** R-G5-6 discharged only when every gate passes; D-classes as their own rows if they are deviations. R-G5-4-a-1 discharged by Phase 1 (or an exact child with a proven RC).
- **Non-goals:** F6; alias-slot policy (R aliases identical L0 frames, G does not; not this row).

### Memory guardrails (all phases)

- Serial under `flock output/.heavy.lock` + `run_heavy_python.py --memory-max 12G` (MemorySwapMax=0). Window and full encodes at `-j4`; K1 ≤ `-j6`.
- Censuses stream block by block (as `dup_census.py`); spool caches bounded (LRU 4096) and cleared; any new scan carries the plan-46 RssAnon watchdog (`--max-rss-mib 3072`).
- Reference peaks: plan 63's dup census R + live + gate_repro reached max RSS 6.94 GiB; its provenance pass 3.71 GiB (`ledger/producer_tie_plan63.json`). Phase 1 must not combine the census with the S′ gate run.
- Encoder dedup memory is one hash set per leaf (bounded by the leaf's record count); measured in the full encode with the `bench_build.py` tree sampler (plan 58: AU tree ~15.3 GB-class).
- OOM or cap trip → stop_for_design with peak. Peaks go into `docs/plans/56-cross-phase-rss-profile/ledger/bg_dedup_plan68.json` + SUMMARY row.

### Scratch hygiene (all phases; Cody standing rule, 2026-10-09)

- **Rule (Cody):** Execute cleans its scratch after every phase, keeping only what the ledger or the next phase needs. **A phase is not done until its scratch is cleared.** The receipt below is part of every phase outcome.
- **This plan's scratch:** `output/scratch-68/`, any git worktree this plan adds (e.g. a `33006aa` sidecar worktree), any temp dir its runs create (named in the run log), and the wrapper's cgroup scopes. Nothing else.
- **Never deleted by this plan:** `output/.heavy.lock` (shared flock file); other plans' `output/scratch-*` (some are pinned evidence, e.g. `oracle_chain/pin_contract.py` pins `output/scratch-32/…`); the spool of record; the R (DVD) image; the disc in force and earlier oracle discs (`0c22b266`, `013586b5`, …); `.venv-rp`.
- **What may be kept:** committed artefacts first. Ledger rows carry the peak fields copied from the wrapper log, so the log itself is not kept. Anything the next phase needs that cannot be committed goes under `output/scratch-68/keep/`, listed with path, bytes and sha256, and is deleted at the end of the phase that consumes it.
- **Receipt** (`scratch_receipt` in the plan note, one per phase):
  1. `du -sb output/scratch-68` before cleanup and after;
  2. after: `test ! -e output/scratch-68` (gone), or `ls -A output/scratch-68` shows only `keep`, with its contents listed;
  3. `git worktree list` shows no worktree from this plan (after `git worktree remove` + `git worktree prune`);
  4. every temp dir named in the phase's run logs is gone, and no wrapper scope from the phase is still running;
  5. kept list checked: every kept path exists, committed paths appear in `git ls-files`, `keep/` items match their recorded sha256.
- A missing or failing receipt means the phase is not done. The final phase ends with `output/scratch-68` gone.

## Decisions

1. Plan number **68**. Master direct. Four phases: R-side truth + R-G5-4-a-1; rule + D-class RC; encoder + windows; successor oracle + residuals.
2. The dedup rule comes from R, not from convenience: keep-first is not assumed even though it is the simplest code.
3. R-noncomparable classes (mostly expected in type 288, where R's mapping differs) are counted and named. Their dedup follows the accepted rule because R holds no duplicate of any type anywhere (0 / 482,473); their *content* parity stays with F6 (Cody).
4. D-classes are measured and root-caused separately; they never borrow the byte-duplicate rule.
5. R-G5-4-a-1 is folded into Phase 1: its 8 groups are byte-identical duplicate pairs and need the same sidecar.
6. Tip `61d2fe8`; live oracle AU `0c22b266…`, Perth `5b86d33e…`.

## Assumption ledger

### Assumption 1

- **Question:** Does "R never duplicates" license removing a copy without knowing R's rule?
- **Answer chosen:** No. It licenses a dedup; which copy survives, or whether R merges, is derived from R (Phase 1–2).
- **Rationale:** Cody's bar: no arbitrary rule called proven.
- **If wrong:** n/a — the stricter path is chosen.

### Assumption 2

- **Question:** Are enough duplicate classes R-comparable to derive the rule?
- **Answer chosen:** Unknown. 99.8% are L0 type 288, where R's content often differs (plan 51: R 0×288 in some parents, 2,203,680×288 nationally).
- **Rationale:** census by type.
- **If wrong:** if a stratum has no R-comparable classes, the rule for it cannot be proven from R. The non-288 types and any comparable 288 classes decide the rule; the remaining stratum is reported as R-noncomparable with its count, and the item goes to Cody alongside F6 rather than being assumed.

### Assumption 3

- **Question:** Will dedup change more than the duplicate leaves?
- **Answer chosen:** Yes, probably: smaller leaves change `dv_shrink` and maybe divisions.
- **Rationale:** plan 51 / 42 (shrink drops roads under 288 pressure); plan 52 division mismatch.
- **If wrong:** the confined-diff gate is simply tighter.

### Assumption 4

- **Question:** Is the plan-63 rule valid on live `0c22b266` (rule was derived on `013586b5` windows at `33006aa`)?
- **Answer chosen:** Not assumed. Between `33006aa` and live the background path changed (3-14 EO stitch `d35b565`, plan 48 `eo_split_on_vertices`, plan 50 supply path; plan 53 touched `dv_assign` only). The live census shows nearly the same duplicate population (336,135 vs 336,329 leaves), which suggests the order survived, but Phase 1 re-checks it with a sidecar on a hash-fixed sample of live windows.
- **Rationale:** plan 63 record ("33006aa"); `git log` of `_cenc.c` / `_e2.c`.
- **If wrong:** the emitter order is re-derived on live before Phase 2; the sidecar patch is ported to the live encoder (output-neutral gate vs `0c22b266`).

## Open questions

1. The exact R reader and the parent-raw geometry decoder for R-one-geom (plan 46 / 63 tooling; Refine names the functions).
2. D-overlap threshold (committed before measuring).
3. Whether the national R-match gate needs a sidecar encode of the successor (to name the surviving copy's emitter) or can use the rule's prediction plus byte position.

## Phases

### Phase 1 — R-side truth on a committed sample; R-G5-4-a-1 discharged

- **Outcome:**
  - `p10_bg_dedup/sample.json` (strata, sample, derivation / holdout split, class definitions) committed before any R read;
  - live + Perth duplicate census with per-copy emitters by plan 63's rule; the rule re-checked on a hash-fixed live sample;
  - `r_correspondence.tsv.gz`: every sampled class → R-one-byte / R-one-geom / R-merged / R-absent / R-noncomparable, with position (first / last / neither) where defined; national counts for framing-equal classes;
  - D-class census (D-rot / D-contain / D-overlap, class 0) on G and R;
  - **R-G5-4-a-1:** `33006aa` sidecar windows for (1664,560), (1694,1781), (1759,1513); per-copy producers for all 8 groups (with (1176,1591) from plan 63's `provenance.tsv.gz`); rule agreement; decide verdict; row discharged or an exact child;
  - double runs byte-identical; peaks in the 56 ledger.
- **Scratch cleared (part of the outcome):** keep `sample.json`, `r_correspondence.tsv.gz` + json, census json / tsv.gz, D-class census, R-G5-4-a-1 verdict file, generators + unit tests (committed); ledger row. Phase 2 reads only these. Delete `output/scratch-68/` contents: the `33006aa` worktree and its window builds, decoded R / live / Perth leaf dumps, alignment intermediates, double-run copies once compared, wrapper logs once copied. Proof: the phase's `scratch_receipt`.
- **Surfaces:** `triage/historical_bg/p10_bg_dedup/`; `parser/tests/`; `residuals.tsv` (R-G5-4-a-1); `docs/provenance.md`.
- **Approach:** known. **Depends on:** none. **Refine:** R reader / geometry decoder names.

### Phase 2 — Dedup rule accepted; D-class RCs

- **Outcome:** `rules.json` scores every candidate rule on derivation and holdout; exactly one rule (or one condition-selected rule set) accepted at 100% with a code path, or "no rule accepted" stated and the plan stops for Design. Preservation contract written as tests. Each D-class that exceeds R has a proven RC (sidecar sample, code path, R correspondence) and a route: same successor or exact child row.
- **Scratch cleared (part of the outcome):** keep `rules.json`, D-class RC files, preservation test specs (committed). Delete scoring shards, D-class sidecar builds and worktrees, temp dirs. Proof: `scratch_receipt`.
- **Surfaces:** `p10_bg_dedup/`; `parser/tests/`.
- **Approach:** open (R's behaviour is not known; the 100% + holdout bar is the yardstick). **Depends on:** Phase 1. **Refine:** candidate list after Phase 1 counts.

### Phase 3 — Encoder dedup on windows

- **Outcome:** the `_cenc.c` / `_e2.c` change with unit tests (unit table, 4,095 split, empty class, divided-leaf probe = emission). Window gates on every sampled cell: non-duplicate leaves byte-identical, duplicate leaves as predicted, K1 failing 0, knock-on decisions listed.
- **Scratch cleared (part of the outcome):** keep the code + tests and `windows_gate.json` (committed). Delete window builds, control builds, K1 window dumps. Proof: `scratch_receipt`.
- **Surfaces:** `parser/kiwiw/_cenc.c` and / or `_e2.c`; `parser/tests/`; `p10_bg_dedup/`.
- **Approach:** open (site per contract; Refine picks). **Depends on:** Phase 2. **Refine:** site.

### Phase 4 — Successor oracle and residuals

- **Outcome:** full AU `-j4` and Perth successors pass every gate in the oracle contract (0 duplicates; R-match where R covers; confined diff with knock-ons traced; R-DVD no-worse; other residual counts re-stated, none up; determinism; close gates a/b/c). Design accept; `successor_oracle_<sha>.json`; OVERVIEW and oracle-chain pin moved. R-G5-6 discharged; D-class rows as decided in Phase 2; tree peak in the 56 ledger.
- **Scratch cleared (part of the outcome):** keep the oracle record, the promoted AU and Perth discs at the disc-in-force path named in the oracle record (outside scratch), census and gate outputs, `residuals.tsv`, ledger row. Delete the whole `output/scratch-68/`: non-promoted encodes, `-j1` determinism build, K1 dumps, decoded discs, tree-sampler raw files, any `keep/`. `0c22b266` is not deleted. Proof: `scratch_receipt` with the path gone.
- **Surfaces:** encoder (landed in Phase 3); `p10_bg_dedup/successor_oracle_<sha>.json`; `docs/OVERVIEW.md`; `oracle_chain` pin; `residuals.tsv`; `causes_residual.md`; 56 ledger.
- **Approach:** known. **Depends on:** Phase 3. **Refine:** skipped.

## Provenance

- Tip GitHub `origin/master` **`61d2fe8`** (plan 63 close-out, 2026-10-09 14:30 AEST). Sources: `residuals.tsv` R-G5-6, R-G5-4-a-1; `docs/plans/63-producer-ambiguous-tie-rc.md` (rule table; dup census; R-G5-4-a-1 note); `p7_producer_tie/{dup_census.py, dup_census_R.json, dup_census_013586b5.json, dup_census_0c22b266.json, provenance.tsv.gz, windows.json, rules.json}`; `p9_r01_residual/transitions.json` (`ambiguous_groups`, sha `d51baafb…`); `docs/plans/62-r01-still-outside-r16.md`; `docs/plans/51-l0-type288-road-trim.md`; `parser/kiwiw/_cenc.c` L31, L1068, L1182; `parser/kiwiw/_e2.c` L304, L596, L746, L988, L1238; `56/ledger/producer_tie_plan63.json`.
- Design Ground on the box: dup-class share by type (from the committed JSON); which a-1 leaves have plan-63 window coverage (`provenance.tsv.gz`, `windows.json`).
- Rejected: keep-first by convenience; treating D-classes as duplicates; discharging on "0 duplicates" without R position; deciding F6 or alias policy here.
- Box draft only. No commit from Design.
