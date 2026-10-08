# Plan 46 — IMPLEMENTATION (DRAFT checkpoint; not landed)

Status: **Execute, re-baseline in progress (Design ruling 09:24, option b)**. Every S-independent figure reproduces exactly at v5. The 3-07 attempt-3 S-dependent figures are retired as a gate. Their root cause is proven by the formula table ("v5 gate: final reconciliation"): each is a function of the unrecorded pin-stop set S. The new baseline is the full S02 predicate, committed and double-run. Nothing is committed to master yet. This file is a running checkpoint.

Basis: 3C-04 / `013586b5` (dump `output/scratch-46/dump_013586b5`, disc `scratch-45/ref_33006aa`,
producer clipper = the disc's own encoder 33006aa `_cenc.c`). Spool
`open-pajero-maps/output/extract_timing/spool`. R = 8 (DESIGN "Locked R").

## Root causes found (each one changed a gate figure; none absorbed)

| # | Cause | Effect before fix | Fix | Evidence |
|---|---|---|---|---|
| RC0 | Producer clipper must be the disc's encoder (33006aa); tip encoder carries the 3-14 fix | unique-byte ~never | `--cenc` pinned export | earlier session |
| RC0b | `_enrich_cands` appended a closing vertex → "explicit closure" always true | inflated bits | raw coords kept | test `unclosed ring not explicit` |
| RC1 | **Byte-145 layout:** `dump_join --mode residual` writes byte 146 but appends the manifest field after the last declared one; the 3-07 s02 extension declares only byte 144, so classify read byte 145 (all zero) → S03/S04 matched 0 | rem 517,785 / 7,456,793 | `gate_repro.declare_byte145` declares byte 145 as `other_mechanism_not_rebuilt` (verified all-zero; 3-08 other_mechanism NOT rebuilt per DESIGN dep. 3); `dump_join.extend_residual` now refuses if the appended field is not declared at 146 (+ test) | gate_repro2 |
| RC2 | **Whole-blob vs per-piece byte match:** a clip may emit several records; each is its own leaf record. `find_producer` compared the whole blob | half of shapes "unique-fragment" | `find_producer(piecewise=True)` (opt-in; 44/45 default unchanged) + `wire_records`; phase23 byte_hit per piece | 300-leaf probe: 168/168 fragment→unique-byte, rbit rows 4,910→8,901 of 9,013; rem → 15,355 / 1,105,637 (gate v3) |
| RC3 | **Far producers:** "bbox-meet" was only a filter inside Moore(R); producers homed > R cells away never became candidates (3-12 used E1 routing over all sources). E.g. (0,1770,203) type 288 ← source (1765,216,rec0), dy=13 (the 3-07 cf_short_ring control source) | 1,007/1,023 remainder fill groups `producer_none` | `FarHomes`: K1 tall set (`cenc.k1_tall`, bbox leaves home±1) indexed by cell bbox ±1; Moore(R) ∪ FarHomes = exact global bbox-meet superset, then the unchanged exact per-ring test | probe R=16: unique-byte (1765,216,0) |
| RC4 | **Divided-leaf clip rect:** `leaf_rect_raw` (design-44 stub) returns the full frame for every depth; E2 `dv_tier_setup` clips a pardiv1/2 sub-leaf to `(sx*cr/nx, sy*cr/nx, (sx+1)*cr/nx, (sy+1)*cr/nx)` on the parent bounds (sub index c = sy*nx+sx; cr = parent slot range) | depth-2 groups `producer_none` (e.g. (0,1832,343,(744,2)) record spans x≤2048, y≥2048) | `leaf_clip_geometry` + `leaf_io.frames(ptype_out=)` (opt-in) | targeted rescan of all remainder leaves: producer_none → 0 (bg 1,132 unique-byte / 8 ambiguous shapes; bb 22,109 / 259) |

| RC5 | **Type of producer:** `clip_ring` forces tc=code, so a same-geometry ring of another type byte-hits too; E2 merge copies the source's own type, so only same-type rings can produce a record | 5 of 7 ambiguous fill groups (e.g. (1252,879) 288/289, (1801,526)) | candidates filtered to `cid.tc == code` in `scan_leaf_rows` | amb7 probe: one same-type hit each, all predicates true |
| RC6 | **Edge-length units:** "closing = longest" was measured in lat/lon degrees; the historical census used `kw_bounds` raw arithmetic (x = lon·cr/dlon, y = lat·cr/dlat). Closure and proper crossings are scale-invariant; "longest" is not | e.g. (1440,833) ← (1440,833,1): closing not longest in degrees (0.865), longest in raw, 1 crossing → 30 fill rows | `bg_ps_ring_stats2(sx, sy)`; scan passes (cr/dlon, cr/dlat) | pred9 probe; test `ring_stats_longest_edge_in_raw_units` |

## S02 pin-stop walk order (retired by Design 09:24; recorded as an unproven hypothesis only)

Tracked evidence: `pinned_candidates.tsv` = the 100 smallest (ix-major) historical S02 groups, min ix 789. All 100 are in scope, qualify in v4, and have identical row counts (100/100). Orders tried (ix/iy-major asc/desc, disc block-key, block/blockset variants, dump order, per-receiver pin keys): none reproduces 25,775 visited with those 100 as the smallest. iy-major and iy-desc cut at 25,772 qualified give exactly 25,775 visited / 3 nomatch, but 1,974,496 / 1,902,777 rows and do not contain the 100. The historical scan script and outputs (`enumerate_S02_attempt3.tsv`, `pins_S02.tsv`, `producer_matches_S02_attempt3.jsonl`) were git-ignored scratch and are deleted.

### Walk-order evidence (08:50 checkpoint, probes `piece_probe/walk3..12.py`, cache `walk_v4.npz`)

- Leaf path p0 = (iy%64)*32 + ix%32 for every candidate (100%): p0 is the cell index in its 32x64 block.
- Inside block (bx,by)=(24,15) the hist-100 split is a clean **p0 prefix**: included p0 <= 1850, excluded (all v4-qualified) p0 >= 1882. So the historical walk visited cells within a block in p0 order and the pin stop fell inside block (24,15).
- But block (25,15) is visited (801,1021/1022 included) while block (24,15) is partial. Disc block order (`disc_order.py`, ref_33006aa: blocksets by index, blocks row-major) puts (24,15) at rank 707 before (25,15) at 708. Every blockset/block row/column-major +/- order (64 combos), global block orders, Morton and Hilbert cell curves: none matches (`walk9.py`, `walk6.py`).
- Ring-set prefixes (producer in hx/hy/block order) fail: a hist ring (796,1018) has excluded groups at (794,1018),(795,1018).
- Dump first-row order: block (25,15) first row 6,005,786 < (24,15) 6,257,264 (the dump interleaves blocks by row). This is the first order that is consistent with (25,15) before (24,15); see walk12.
- The 3 historical no-match groups (all iy 395, block (56,6)) are status-1 qualified in v4 (RC2-RC4 fixed them), so they cannot mark visitation in v4.
- Historical artefacts: `output/scratch-3-07`, `scratch-3-08` are dangling symlinks in `open-pajero-maps-3-14/output`. A filesystem search found no `pins_S02*`, `enumerate_S02*`, `*attempt3*`, and `pin_producers_attempt3.py` was never committed (git log --all).

- Dump first-row order (walk12): hist-100 ranks span 26,291..51,540, and excluded (794,1018) sits at 51,254 inside that span. Not a prefix either.
- In-flight (parallel block completion) hypothesis (walk13-17): candidate blocks in disc order, hist blocks at ranks 492/684/700/707/708. The disc prefix through 708 is 30,687 groups / 2,352,941 rows, so blocks would need to be removed: G 4,912, R 413,569, all-sentinel A 103. The removal sum is reachable over 68 blocks (subset-sum), but no set of 4 or fewer blocks matches. That is not unique, so it is **not proof**.

### S02-dependence identities (proved on the gate pipeline definitions)

S = the S02-qualified group set fed to cls1. Residual population = cls1 NO_RULE rows.
- entries(S) = E_fix - |S| + c_cover. v4: 421,941 = E_fix - 29,244, so E_fix = 451,185. Hist: 425,416 = 451,185 - 25,772 + c, so **c = 3**, which falls inside the interior_cover bound 3..6. **res_entries reconciles exactly** once the S02 count difference is accounted for.
- res_bnd_groups(S) = T - a(S), where a = the number of all-sentinel groups in S (a group with any non-sentinel row stays residual). There are 15,080 all-sentinel groups among the 145,960 candidates. v4 a = 4,489, so T = 219,201, and hist 216,488 implies **a_hist = 2,713**. That cannot be checked without the historical S.
- s02 rows/groups, visited/nomatch and residual rings are functions of S as well. The remainder does not depend on S.

## S02 scope (named, reproduced by replay)

Historical S02 = 3-07 attempt-3 **pin-stop prefix**: candidate groups (S02 column predicate L0/291/sentinel)
walked in `k1_triage enumerate` order (sorted full group key; review_3-07 L29 "block-key order"), stop
when distinct source rings > 10,000. The pin list files are deleted, so `gate_repro` replays the walk.
Candidate scope on 013586b5 = **145,960 groups / 11,127,845 rows = historical exactly**.
Full-predicate S02 (v3): 142,036 groups / 10,887,453 rows (reported, not used for the gate).
The final remainder is invariant to S02 scope: s02 ⇒ rbit for every group (checked: 0 violations).

## interior_cover

DESIGN non-goal ("non-background kinds"); not in the dump. Its 3 groups bound the gap: entries 3..6,
rings 0..3 (`gate_result.json.cover_bound`).

## Gate history

| Run | s02 rows/groups (pinstop) | visited / nomatch | res entries / fill / bnd | rings | rem fill / bnd |
|---|---|---|---|---|---|
| hist | 1,939,053 / 25,772 | 25,775 / 3 | 425,416 / 30,558 / 216,488 | 70,999 | 137 / 8,739 |
| v2 (blob, full S02, RC1 open) | 9,093,250 / 106,113 (full) | – | 345,072 / 30,558 / 211,284 | 66,993 | 517,785 / 7,456,793 |
| v2 + RC1 | same | – | same | same | 184,102 / 3,980,980 |
| v3 (RC2, pinstop) | 2,178,818 / 27,477 | 29,395 / 1,918 | 423,708 / 30,558 / 215,434 | 69,855 | 15,355 / 1,105,637 |
| v4 (RC3+RC4, pinstop) | 2,288,062 / 29,244 | 29,248 / 4 (204 rows) | 421,941 / 30,558 / 214,712 | 70,981 | 217 / 12,879 (16 / 325 groups) |
| **v5 (RC5+RC6, pinstop)** | 2,288,116 / 29,246 | 29,248 / 2 (150 rows) | 421,939 / 30,558 / 214,712 | 70,982 | **137 / 8,739 (11 / 169 groups) = hist exactly** |

v4 notes (08:30): full-predicate S02 145,940 / 11,126,430 of 145,960 / 11,127,845 candidates. Fill: 30,542 status1 vs 30,547. Of 16 remainder fill groups, 7 are producer_ambiguous; in 5 exactly one hit has the record's type (a source of another type cannot produce the record: E2 merge copies the source's own type; probe forces tc=code) -> RC5 candidate (same-type filter) gives 30,547 / 11 groups exactly. Open: S02 pinstop walk order (see above) (hist 25,775 visited) and row-level 165 vs 137.

v5 scan (RC5+RC6) complete 09:07 (wall 1,426 s): bg 1,438,571 rows, bb 16,550,043 rows (both complete); cgroup memory_peak 4.69 GB (includes file pages); max shard sampled RssAnon 928.6 MiB; exit 0. Gate run gate_repro5 09:08-09:19 (436 s wall inside the wrapper, the rest waiting on the lock), exit 0, max RSS 6,395,748 KiB, cgroup peak 5,753,118,720 B (runs/gate_repro5.json). **Remainder 137 / 8,739 reproduced exactly; fill status-1 30,547 = hist; res fill groups 30,558 = hist.** Full-predicate S02: 145,954 / 11,127,333 of 145,960 / 11,127,845. entries: 421,939 + 29,246 = 451,185 = E_fix, so hist c_cover = 451,185 - 25,772 - 425,416... (425,416 = 451,185 - 25,772 + 3) -> c = 3 in bound. Open: only S-dependent figures (S02 rows/groups, visited/nomatch, res bnd groups, res rings).

## Memory root cause (OOM at 06:18) and bound

- Cause: decoded-cell cache (60k cells) + `_RING_NP` (60k, Python coord lists) + per-shard Python
  grouping of all rows + poor spatial locality → RSS linear growth, 7.4 GiB/shard when killed.
- Fix: LRU 4096 numpy-only ring cache; vectorised tiled leaf order (cache shared by shards);
  streaming TSV.gz; RssAnon watchdog `--max-rss-mib 3072` (exit 3); cgroup `MemoryMax=12G`,
  `MemorySwapMax=0` via `run_heavy_python --memory-max`; trap launcher (no orphan pass).
- statm RSS counts memmap file pages → watchdog uses RssAnon.
- Measured: probe 5k leaves cgroup peak 3.64 GB; scan v2 cgroup memory.peak 3.36 GiB (4 shards),
  max shard RssAnon 935 MiB; scan v3 2.11 GB / 935 MiB; gate_repro peak 4.49–5.77 GB (cgroup).



## v5 gate: final reconciliation (09:30)

S-independent figures (v5), all **exact**:
- remainder fill 137 rows / 11 groups and boundary 8,739 rows;
- cls2 R01 920,786;
- S03 517,648 rows / 30,547 groups / 24,731 rings (causes_residual table);
- residual fill groups 30,558;
- total boundary spool S02+S04 = 2,288,116 + 14,253,188 = **16,541,304 = hist**;
- S02 candidate scope 145,960 / 11,127,845.

S-dependent figures. Each one is an exact function of the historical S02 set S. The identities are validated on v5 by `piece_probe/rings6.py`, which recomputes the gate's values:

| Figure | Hist | v5 (replay S) | Identity | Implied hist |
|---|---|---|---|---|
| S02 rows / groups | 1,939,053 / 25,772 | 2,288,116 / 29,246 | rows(S), \|S\| | – |
| S04 rows | 14,602,251 | 14,253,188 | 16,541,304 - rows(S) | consistent |
| res entries | 425,416 | 421,939 | 451,185 - \|S\| + c_cover | c_cover = 3 (bound 3..6) |
| res bnd groups | 216,488 | 214,712 | T - a(S), T = 219,201 | a(S) = 2,713 |
| S04 groups (bb st1 residual) | 216,319 | 214,543 | 219,032 - a(S) | a(S) = **2,713** (independent figure, same a) |
| res rings | 70,999 | 70,982 | f(S n allsent); range 70,861..71,052 | 70,996..70,999 is inside the range |
| S04 rings | 70,911 | 70,837 | bb-only; range 70,396..71,041 | inside the range |
| visited / nomatch | 25,775 / 3 | 29,248 / 2 | walk(S) | – |

a(S) = the number of all-sentinel groups in S; there are 15,080 of them among the candidates.

Historical no-match groups (1792,395,352,6), (1801,395,361,10) and (1805,395,365,517) are unique-byte status 1 in v5, with producers (1792,396,4), (1801,396,0) and (1805,396,171). They were no-match in 3-07, before RC2-RC4. The v5 no-match groups in the replay are (1481,1288,p265, shapes 0 and 2), 2 x 75 rows: producer_ambiguous, meaning two same-type byte-identical candidates.

## Former blocker (for Design; resolved by the 09:24 ruling below)

S is the 3-07 attempt-3 pin-stop prefix. The walk script (`pin_producers_attempt3.py`, never committed) and its outputs are gone: `output/scratch-3-07` is a dangling symlink, and a filesystem search finds nothing. The visited set is **not a prefix of any deterministic order tested**: sorted key, iy/ix asc/desc, 64 blockset/block orders, Morton, Hilbert, disc block order, frame-dsa order, dump order, and ring orders.

The tracked hist-100 shows two things. Within block (24,15) the visited cells form a clean p0 prefix (<=1850 in, >=1882 out). But block (25,15) was visited, and it comes after (24,15) in disc and frame order. That pattern fits out-of-order (parallel) block completion. A subset-sum over blocks can reach the target, but no small set of in-flight blocks fits, so this is not proven.

S therefore cannot be reconstructed. The S-dependent gate figures can be reconciled only through the identities above, not row by row. Design must decide one of:
- (a) accept the identity reconciliation plus the exact S-independent figures as the Phase 1 gate (named difference: unrecorded S02 pin-stop subset);
- (b) re-baseline the S02-dependent historical figures on a recorded S, for example full-predicate S02 145,954 / 11,127,333 or the sorted-key replay;
- (c) something else.

Phase 2/3 and the residual updates are not started until Design decides.


## Design ruling (09:24): option (b), keeping (a)'s reconciliation as the root cause

- The 3-07 attempt-3 S-dependent figures are retired as a gate. Root cause for every S-dependent delta: the historical figure is a proven function of S, and S was never recorded (`pin_producers_attempt3.py` was never committed; `scratch-3-07` is gone). The formula table above is the proof. Parallel out-of-order completion is recorded **only as an unproven hypothesis**, never as the cause. No further orders will be tried.
- The re-baseline uses the FULL S02 predicate (145,954 / 11,127,333) with no pin stop. S itself is committed (sorted group list, or hash plus generator). Double run, with counts and identity table required to be byte-identical.
- The scope vs predicate delta (6 groups / 512 rows) needs a named cause.
- (1481,1288): if the candidates are byte-identical over the whole compared extent, it becomes proven-producer-tied with a lowest-key tie-break and both IDs recorded. Otherwise it stays open with an RC owed.
- The 929 MiB shard peak goes into the plan-56 RSS ledger.
- Re-baseline started 09:27 (`runs/rebaseline.sh`): gate A (full) on the v5 scan, then scan B, then gate B, then a hash compare. Superseded pinstop gatework dumps were deleted; cls/side were kept in `gatework_v5_pinstop`.

## Full-predicate re-baseline: gate A (09:45, `gate_repro --s02-scope full`, v5 scan)

S = the full S02 predicate, with no pin stop. It is committed as `p6_producer/s02_full_predicate_groups.tsv.gz`: 145,954 groups / 11,127,333 rows, sorted by the full group key, gzip mtime=0. The uncompressed TSV has sha256 `ae2ce385…8d04` and the .gz has `7ab5a029…42fa` (912,601 B). The generator is `p6_producer/s02_list.py <work> <out>`.

| Figure | 3-07 hist (retired as gate) | Full-predicate baseline (A) | Identity check |
|---|---|---|---|
| S02 rows / groups | 1,939,053 / 25,772 | **11,127,333 / 145,954** | = S |
| S04 rows | 14,602,251 | **5,413,971** | 16,541,304 − 11,127,333 ✓ |
| res entries (fill+bnd; + cover 3) | 425,416 | **305,231** (+3 = 305,234) | 451,185 − 145,954 + 3 = 305,234 ✓ |
| res bnd groups | 216,488 | **204,123** | 219,201 − a(S), a(S) = 15,078 ✓ |
| S04 groups (bb status-1 residual) | 216,319 | **203,954** | 219,032 − 15,078 ✓ |
| res rings (fill+bnd) | 70,999 | **70,861** | lower end of the feasible range (all qualified all-sentinel groups removed) ✓ |
| visited / nomatch | 25,775 / 3 | n/a (no walk) | – |

a(S) = 15,078 was counted directly: 15,080 all-sentinel candidates, minus the 2 non-qualified groups (1481,1288) shapes 0 and 2, which are all-sentinel. This is a third independent check of the identities (after v4 and v5): both T-identities give the same a(S), matching the direct count.

S-independent figures in gate A, all exact (Phase 1 gate):
- rem fill 137 / 11 groups; rem bnd 8,739 / 169 groups;
- R01 920,786;
- S03 517,648; bg status-1 30,547;
- res fill 30,558;
- S02+S04 = 16,541,304;
- scope 145,960 / 11,127,845.

The remainder is unchanged from pinstop v5, as expected (s02 ⇒ rbit).

`cover_bound` in gate_result_full.json compares against the retired 3-07 figures, so its "false" is expected. It is not a gate under the ruling.

### Scope vs predicate delta (6 groups / 512 rows): named cause

The 6 scope groups that fail the full predicate are exactly the S02-candidate groups whose v5 scan status is `producer_ambiguous`. Each has two or more same-type candidates whose per-piece clip byte-hits the record, so `status != 1`.

| Group | Rows | All-sentinel |
|---|---|---|
| (1481,1288,p265) shape 0 | 75 | yes |
| (1481,1288,p265) shape 2 | 75 | yes |
| (1753,1158,p217) shape 1 | 119 | no |
| (1753,1158,p217) shape 2 | 119 | no |
| (1754,1158,p218) shape 1 | 62 | no |
| (1754,1158,p218) shape 3 | 62 | no |

Total: 512 rows / 6 groups = 11,127,845 − 11,127,333 and 145,960 − 145,954. The tie probe (`p6_producer/tie_probe.py`) decides proven-producer-tied versus RC owed for each group (see below).

### Double run (09:27–10:15, `runs/rebaseline.sh` under `run_heavy_python --memory-max 12G`)

Run A: gate on the v5 scan. Run B: an independent fresh scan (`gate_b`) followed by its own gate (`gatework_full_b`). Wrapper totals: wall 2,175.6 s, max RSS 7,919,356 KiB, cgroup memory.peak 7,850,299,392 B (cap 12G, not hit). Scan B: bg 09:45:26–09:51:51, bb 09:51:51–10:08:51.

The script printed `DOUBLE_RUN_DIFF` (exit 4). The only differing file is `dump_ext/dump_manifest.json`, which embeds the work-dir path (`gatework_full_a` vs `gatework_full_b`) in the `side_table` / `source` / `side_tables` strings. With that path normalised the manifest is identical (sha `d272a0a5…`). This is a known non-data difference, not a divergence.

Every data artefact is byte-identical across A and B, 34 of 34:
- 8 scan TSV contents and 8 side.npy;
- cls1 and cls2 assign/cause_counts/partition/rules/unclassified;
- dump_ext background.bin and background_boundary.bin;
- side s02/side tables;
- joined_counts.json.

All sections of `gate_result_full.json` are equal between A and B (measured, s02_full_predicate, s02_candidates, compare, …). S from B is identical to the committed list: `s02_list.py` on `gatework_full_b` gives a byte-identical .gz (`7ab5a029…`), with TSV sha `ae2ce385…8d04`. **Double run: identical (counts + S + all data artefacts).**

### Tie probe (10:21, `p6_producer/tie_probe.py`, run_heavy_python: max RSS 3,885,200 KiB, wall 5.5 s; `runs/ties.json`)

Criterion (ruling): *byte-identical over the whole compared extent* means the full clip blob into the leaf, covering all pieces, not just the matching piece. Only same-type candidates are considered (RC5). In every case both shapes of a leaf hit the same two candidates.

| Group (shapes) | Candidates (hx,hy,ri,type) | Clip blob | Source ring | Outcome |
|---|---|---|---|---|
| (1753,1158,p217) 1, 2 | (1755,1157,1,291), (1755,1157,2,291) | **identical** (`e5b7534e…`, 1 piece) | differ (240 vs 375 vertices) | **proven-producer-tied**; tie-break lowest key → (1755,1157,1) |
| (1481,1288,p265) 0, 2 | (1485,1280,0,291), (1486,1280,0,291) | differ (2 pieces each) | differ | **open: RC owed** |
| (1754,1158,p218) 1, 3 | (1755,1157,1,291), (1755,1157,2,291) | differ (2 pieces each) | differ | **open: RC owed** |

The 2 groups / 238 rows of (1753,1158) are proven-producer-tied. The other 4 groups / 274 rows (2×75 + 2×62) stay open with an RC owed. They do not qualify under the full predicate, so they are outside S and stay in the residual/S04 population; the S baseline is unchanged. A per-piece follow-up (`ties2.json`: piece shas, which leaf shapes each piece lands on, and whether every piece of each candidate's clip exists on disc) is recorded as evidence toward that RC. It does not reclassify anything.

## Phase 2: identity table (10:22, `runs/phase23.sh` under run_heavy_python; max RSS 3,905,180 KiB, cgroup peak 6,097,743,872 B, wall 87 s)

`phase23.py identity` joins the cls2 NO_RULE rows of the full-predicate gate to the scan TSVs. Output gzip has mtime=0 and no name, so it is deterministic.
- A (`gatework_full_a` + v5 scan) → `p6_producer/identity_remainder.tsv.gz`: background 137 + background_boundary 8,739 = **8,876** rows; sha256 `96093444…7603`, content `28cb90fb…5f87`.
- B (`gatework_full_b` + independent scan `gate_b`) → byte-identical (`IDENTITY_IDENTICAL`).
- **R-G8-4-c discharged** (8,876 old identities committed, sha-pinned).

## Phase 3: per-row decisions (`phase23.py decide`, run twice → `DECIDE_IDENTICAL`)

Inputs: old disc 33006aa ref (013586b5…), new disc d35b565 ref (4ed9cd80…), exclusivity clipper d35b565 `_cenc.c` (5c43e00d…), R=8 plus far bbox-meet homes. Output `p6_producer/verdicts.tsv.gz`: sha256 `ca4a555a…ec96`, content `775ac6c0…4b81`.

| Kind | Verdict | Rows | Groups | Residual row |
|---|---|---|---|---|
| background | build:eo_bg_stitch (byte 119/119; OE vertex also 119) | 119 | 9 | R-G5-2 discharged part |
| background | producer_ambiguous | 18 | 2 | **R-G5-2-a** |
| background_boundary | build:eo_bg_stitch (byte 4,095; 4 by byte only, 4,091 byte+OE vertex) | 4,095 | 72 | R-G5-1 discharged part |
| background_boundary | producer_ambiguous | 4,594 | 96 | **R-G5-1-a** |
| background_boundary | source-removed: producer (1751,594,16) clips to empty on d35b565 | 50 | 1 ((0,1750,594,(598,3)) shape 171, type 288) | **R-G5-1-b** |
| **Total** | | **8,876** | **180** | |

The 98 producer_ambiguous groups are the same count as the historical "2+ candidate rings" class in `causes_residual.md`. They remain named residuals (no nearest-ring choice, no tie rule beyond the ruling's whole-blob identity). The "not failing on 4ed9cd80" clause cites K1 `k1head_314` / `k1old_314` (bg family failing 0) per row.

## Final baseline and gate table (Design ruling b)

| Figure | Retired 3-07 | **Baseline (full predicate, double-run identical)** | Status |
|---|---|---|---|
| rem fill / bnd | 137 / 8,739 | 137 (11 g) / 8,739 (169 g) | **exact** |
| cls2 R01 | 920,786 | 920,786 | **exact** |
| S03 rows / bg st1 groups / bg rings | 517,648 / 30,547 / 24,731 | 517,648 / 30,547 / 24,731 (v5) | **exact** |
| res fill groups | 30,558 | 30,558 | **exact** |
| S02+S04 spool rows | 16,541,304 | 11,127,333 + 5,413,971 = 16,541,304 | **exact** |
| S02 scope | 145,960 / 11,127,845 | 145,960 / 11,127,845 | **exact** |
| S02 (S) | 1,939,053 / 25,772 | **11,127,333 / 145,954** (committed list) | new baseline; delta = proven function of unrecorded S |
| res entries | 425,416 | **305,231** (+3 cover) | new baseline; identity ✓ |
| res bnd groups | 216,488 | **204,123** | new baseline; identity ✓ (a = 15,078) |
| S04 groups | 216,319 | **203,954** | new baseline; identity ✓ |
| res rings | 70,999 | **70,861** | new baseline; in feasible range |
| visited / nomatch | 25,775 / 3 | n/a | retired with the pin stop |

Scope vs predicate: 6 groups / 512 rows, all producer_ambiguous. Of these, (1753,1158) shapes 1 and 2 (238 rows) are proven-producer-tied with lowest-key tie-break (1755,1157,1), and both IDs (1755,1157,1/2) are recorded. (1481,1288) shapes 0/2 and (1754,1158) shapes 1/3 (274 rows) stay open with an RC owed.

RC evidence for Design (`ties.json`, not a reclassification): in both open leaves the two scoped shapes are byte-identical duplicate records, P. Each candidate's clip emits P plus one other piece, and those other pieces are distinct leaf records: (1485,1280,0) → shape 1, (1486,1280,0) → shape 3; (1755,1157,1) → shape 2, (1755,1157,2) → shape 4. Every piece of both candidates' clips exists on disc. This fits "each candidate produced one copy of P". It is not proven under the whole-blob criterion.

## Memory

- Scan v5: max shard RssAnon 928.6 MiB (cap 3072), wrapper max RSS 4,603,056 KiB, cgroup peak 4.69 GB.
- Re-baseline double run: max RSS 7,919,356 KiB, cgroup peak 7.85 GB.
- phase23: 3.9 GB / 6.10 GB.
- tie probe: 3.9 GB.
- All under MemoryMax 12G. Added to the plan-56 ledger (`ledger/bg_producer_scan_plan46.json` + SUMMARY row).

## Progress
- [x] Phase 1 S-independent exact; S re-baselined on the full predicate, committed, double run identical; delta named
- [x] Phase 2 identity table (R-G8-4-c)
- [x] Phase 3 decisions (R-G5-1 / R-G5-2 → discharged parts + children R-G5-1-a/b, R-G5-2-a)
- [x] residuals.tsv, causes_residual.md note, OVERVIEW, plan-56 ledger
- [ ] commit + push, Flash review, close-out
