# BG duplicate-record dedup (R-G5-6 / R-G5-4-a-1): R-side truth, rule scoring — closed at Phase 2 as a findings plan

## Intent
Plan 63 opened R-G5-6: G emits byte-identical same-type class>0 background records in one leaf. Plan 68 was to establish what R does where G has duplicates (one copy at an emission position, merged, or absent) on a committed sample with a hash-fixed holdout, accept a dedup rule at 100 % on derivation and holdout, land it in the encoder and promote a successor oracle; Phase 1 also decided R-G5-4-a-1.

Design: box draft `68-bg-duplicate-record-dedup/DESIGN.md` (sha256 `f6372e2a…`, re-copied fresh 2026-10-09 ~15:45 AEST), base `61d2fe8`, worked at `c5d329c`. Seat: Codex; Flash for the re-review (CHM seat change 19:21).

## Outcome
- **Commits:** P1a `f8b572d`; P1 checkpoint `1f7a7be`; P1 close + P2 `00a021a`; reader re-audit `451cf60`; review-1 fixes + ruling `cc3fcbb`; review-2 fixes + close-out (this record).
- **R-G5-4-a-1 (222 rows / 8 groups): discharged-plan-68**, all build:eo_bg_stitch (`p10_bg_dedup/a1_verdicts.json`).
- **Finding:** plan 63's "R holds 0 duplicates" was a reader artefact (the `frame[:U16(frame,0)*2]` cut drops every R record). Read whole, R holds 486 duplicate classes in 258 leaves. Reader re-audit: this is the only conclusion that changes; every G-side claim of plans 63 / 64 / 68 stands (cut lossless on all three G discs), and plan 64's "R has 0 type-288 polygons in the 23 cells" stands.
- **No dedup rule accepted** (`rules.json`): 0 R-one-byte / R-one-geom classes in the committed sample and in the 2,164 national framing-equal classes. Where R is comparable it mostly has nothing of that type (R-absent) or another type (type-set).
- **Closed at Phase 2 (Design ruling 2026-10-09 17:23).** P3/P4 cancelled; drop-all not implemented; no encoder or oracle change (`0c22b266…` / `5b86d33e…` stay in force).
- **Phase 4 gate withdrawn and rewritten** (the draft's gate — "`dup_census.py` on the successor reports **0** leaves with byte-identical same-type class>0 duplicates at every level" and the Phase 4 outcome's "(0 duplicates; …)" — no longer applies): R itself holds 486 such classes, so "0 duplicates" is not R parity. Any future successor gate for this class reads: *G duplicate classes where R holds no copy → 0 (per the R-G5-6-a / -b remedy), and R's own duplicate classes (R-G5-6-c) reproduced where G and R frames are comparable; neither side measured through the truncating cut.* The draft copy is removed with the plan folder; this record is the plan text of record.
- **R-G5-6 split:** R-G5-6-a (L0 type 288 content; 338,038 G duplicate classes + 98.5 % of 18,859,711 G AU D-class pairs; Cody with F6 and the plan-64 open-ways finding), R-G5-6-b (527 non-288 G duplicate classes + drop-all mismatches 10/135, 8/149; Design), R-G5-6-c (R's own 486 classes / 258 leaves; Design).
- **Recorded process deviation (accepted by Design):** the Phase 2 scoring read (33 MB, 0.07 s, committed inputs) ran outside the flock wrapper; every heavy run was under flock + `--memory-max 12G`.
- Peaks (56 ledger `bg_dedup_plan68.json`): review-1 rerun max RSS 3,742,820 KiB / memory.peak 11.19 GB incl. file pages, 4,968 s; P1a 3,580,680 KiB / 8.52 GB; P1c 3,742,280 KiB / 4.73 GB; P1d/e 1,583,952 KiB / 4.59 GB; reader re-audit 317,276 KiB / 4.04 GB.

## Review
Codex (read-only), review 1: **FIX** — five findings (crossing rings in `near()`, one-way D-contain, missing tests / double runs, "never" overstated, 98.9 % → 98.5 %). Fixed in `cc3fcbb` with reruns (A == B).
Codex re-review attempt 19:32 aborted (Codex usage limit); re-review on OpenCode DeepSeek Flash (read-only `plan` agent): **FIX** — (1) P4 gate text still "0 duplicates" in the draft copy → withdrawn and rewritten above, draft copy removed with the folder; (2) artefact hashes pre-fix → updated; (3) per-type "Next:" D-class figures pre-fix → updated; (4) ledger top-level peak understated → set to the rerun; (5) citations of this record file dangling → resolved by this record. Fixed in this close-out.

## Implementation log (collapsed from IMPLEMENTATION.md)

Seat: Codex on codyh-ubuntu (master direct). Draft re-copied fresh from the box `/workspace/maps-design-drafts/68-bg-duplicate-record-dedup/DESIGN.md` at start (2026-10-09 ~15:45 AEST, sha256 `f6372e2a…`). Base: `origin/master` `c5d329c` (plan 64 close-out; the draft grounds at `61d2fe8`, and `61d2fe8..c5d329c` touches docs and triage tools only, no encoder change). Live oracle AU `0c22b266…`, Perth `5b86d33e…`, both built from `output/scratch-50/spool_overlay` (manifest `output/scratch-53/G_new/manifest.json`).

Hard stop: Phase 4 gate summary → report for Design accept before any oracle promotion.

## Phase 1 — R-side truth on a committed sample; R-G5-4-a-1 (done 17:21 AEST; review fixes + double runs 19:4x AEST, see Review 1)

### Refine (fixed before any R read)

1. **Emitters on live (Assumption 4).** Plan 63's `sidecar_33006aa.patch` applies unchanged at tip (`git apply --check` clean; `_cenc.c` / `_e2.c` last changed by plan 53 `afce673`). Throwaway worktree `../open-pajero-maps-68-sidecar` at `c5d329c` + patch. Because a full AU encode is ~30 s at `-j4` (plan 53 ledger), the sidecar is run on the **whole of AU and Perth**, not a window sample. Output-neutral gate: full-disc sha256 equal to `0c22b266…` / `5b86d33e…`. Per-copy emitters are then national, and the plan-63 rule is re-checked on every duplicate class, not a sample.
2. **Census tool** `p10_bg_dedup/census.py`: plan-63 duplicate definition (class>0, same type, byte-identical, distinct frames, alias slots read once); per copy (record index, class, merged ordinal, source kind / cell / shape k) from the sidecar (W lines for whole cells, F+P for divided sub-cells, frame matched by FNV hash and record count / class sequence). Rule check per class: copies in leaf order strictly increasing in merged ordinal and in (class, own-first, source iy, ix, k).
3. **R reader (open question 1).** Plan 48's: `overlay_test.RReader` + `r_neighbours.LeafIndex` + `decode_parcel` (as `trim_witness.r_parent`), used identically on the G disc so both sides decode through one path; wire bytes via plan 63's `leaf_all_records`.
4. **Sample strata (G-side only).** (level, type, copies 2 | 3+, depth 1 | 2+, emitter form cover | ring | mixed from the sidecar kind). Framing equality vs R needs R's leaf index, which is an R read, so it is a measured column of the correspondence rather than a stratum. K = 60 per stratum, K = 240 for L0/288 strata (99.8 % of classes); smaller strata taken whole. Pick and holdout keys exactly as the draft (`p68-sample:` / `p68-holdout:` over `{level},{ix},{iy},{path},{sha}`).
5. **Class definitions** (in `sample.json`, before any R read): R-one-byte, R-one-geom, R-merged, R-absent, R-noncomparable (alias frame | type-set), plus R-other (named per case, never a pass). Tolerance 1 parent-raw unit. Position: first / last / middle / neither by anchor alignment on unique byte- or geometry-equal non-duplicate records.

### P1a — live sidecar encodes and national census (done, 16:00 AEST)

Wrapper `run_heavy_python.py --memory-max 12G` (flock; waited behind another agent's e2e job holding `.heavy.lock`): max RSS 3,580,680 KiB, memory.peak 8.52 GB (incl. file pages), 170 s.
- **Output-neutral gate:** full AU sidecar encode sha256 = `0c22b266…` (equal); Perth = `5b86d33e…` (equal). The sidecar disc was deleted after the gate; the census reads the oracle copy.
- **AU census** (`census_au.json` / `.tsv.gz`): 336,135 leaves with duplicates, 338,565 classes, 444,934 extra copies (equal to plan 63's `dup_census_0c22b266.json`). Every duplicate leaf matched to its sidecar entry (334,709 whole-cell W, 1,426 divided-sub-cell F+P), 0 unmatched, 0 count / class-sequence failures.
- **Perth census:** 1,812 leaves, 1,987 classes, 2,573 extra copies; all matched.
- **Plan-63 rule on live, national:** 338,565 / 338,565 AU classes and 1,987 / 1,987 Perth classes have copies in strictly increasing merged ordinal and (class, own-first, source iy, ix, k) order; 0 shared emitters (every copy from a distinct source). Assumption 4 holds on live without re-derivation.
- **Emitter form:** 768,130 of 783,499 AU copies are E1 interior-cover items (kind 1, a source whose ring covers the whole leaf); 242,645 of the 338,565 classes are cover-only pairs at L0/288.
- **Sample** (`sample.json`): 2,472 classes in 31 strata (derivation 1,237 / holdout 1,235), committed before any R read.

### P1b — finding: plan 63's R duplicate census was vacuous; R does hold duplicates (16:20 AEST)

- A 40-row tool probe of the correspondence (not a scoring run) failed to align R leaves: plan 63's `leaf_all_records(frame[:U16(frame,0)*2])` returns **no records** for R frames. On G discs word 0 is the frame length / 2; on R it is not (R frame (0,1834,340,(650,)) truncates to 140 bytes, losing road / background / name sections).
- `p10_bg_dedup/r_census.py` (reads each distinct R frame whole; section offsets bound every read; counts both ways): over all 482,473 distinct R frames, the truncated read yields **0 records at every level** (`records_trunc` 0; 446,505 frames lose records), so `dup_census_R.json` ("0 of 482,473") measured nothing. Whole-frame read: 1,315,200 class>0 records.
- **R holds byte-identical same-type class>0 duplicates: 258 leaves, 486 classes, 486 extra copies** (all pairs). By level/type: L0 291 197, 321 9, 640 45; L2 291 189, 321 13, 640 26; L4 321 5; L6 321 2. No type 288. Copy positions: adjacent (gap 1) in 299 / 486, gaps 2–9+ otherwise.
- **No R duplicate class coincides with a G duplicate class** (same level, cell, type: 0 of 486); 132 of the 486 R classes sit in cells where G has duplicates of another type.
- Consequence for the plan (to Design at the Phase 1 report): R-G5-6's ground "R never does (0 / 482,473)" is false as measured; the P4 gate "0 duplicate leaves" is not by itself R parity. Phase 1 continues (the R correspondence measures what R holds where G duplicates). `r_corr.py` reads R wires from the whole leaf entry.

### P1c — R correspondence, national framing-equal counts, R-G5-4-a-1 (done ~16:20 AEST; checkpointed 16:35 after interruption)

Seat note: CHM 15:54 — Codex at its 5 h limit until 17:14; any new harness seat before 17:15 goes on OpenCode DeepSeek Flash. Work here is run directly on codyh-ubuntu; only reviews use a seat.

- **Sample correspondence** (`r_corr.py`, 2,472 classes; runs A and B byte-identical): **R-one-byte 0, R-one-geom 0**; R-merged 1; R-absent 266 (231 no type in cell, 30 type elsewhere in cell, 5 R outside coverage); R-noncomparable 2,188 (alias 1,497, type-set 691); R-other 17. By split: derivation absent 125 / merged 1 / noncomparable 1,102 / other 9; holdout absent 141 / noncomparable 1,086 / other 8.
  - Alias rows, geometry class inside R's shared sparse-tile frame (measured, never a pass): absent 595, type-set 674, other 228, **no one-byte / one-geom**.
  - R-other (17): an R same-type record overlaps or contains the piece with different geometry (types 321, 289); none equal.
- **National, framing-equal** (`--all-census`, every census class prefiltered on R's leaf index without decode): 338,565 = R alias frame 334,466 + frame differs 1,852 + no R leaf 83 + **framing-equal 2,164**. The 2,164: R-absent 541, R-noncomparable(type-set) 1,609, R-other 13, R-merged 1, **R-one-byte 0, R-one-geom 0**.
- **Reading:** in the committed sample and in the 2,164 national framing-equal classes, R never holds exactly one copy of a G duplicate piece (the 1,852 national classes whose frames differ, the 334,466 R-alias and 83 no-R-leaf classes are not classified). Keep-first / keep-last / keep-own-first have no R-one-* class to score on; R's behaviour where comparable is "nothing of that type there" (absent) or "another type maps the area" (type-set, the F6 question), plus 14 merged/other cases.
- **R-G5-4-a-1** (`a1.py`; 4 single-cell `33006aa` sidecar windows from the spool of record; runs A/B identical): gate 4/4 frames byte-equal to 013586b5, 0 unmatched; all 8 groups: copies emitted by the two plan-62 tie candidates, one each (distinct), plan-63 rule order holds, decide verdict under the proven producer of the group's shape = build → **222 rows / 8 groups build:eo_bg_stitch**. (1176,1591) agrees with plan 63's `provenance.tsv.gz`.
- Peaks: p1c max RSS 3,742,280 KiB / memory.peak 4.73 GB, 346 s; p1d (a1) within 1.06 GB.

### P1d — D-class census (done 17:12 AEST)

- First Perth run stopped by pid after ~10 min (no output): a 48×48 grid containment test costs ~10 s per dense urban leaf (1,800+ type-288 records, thousands of nested pairs). Definitions revised **before any measuring run completed** (tool probes only): D-contain by a vertex criterion, grid (24×24) only for the overlap area. See `dclass.py` docstring.
- Runs: Perth G alone (`dclass_perth`, 317 s, max RSS 488,124 KiB); then p1e = R (`--whole`) + AU G (`0c22b266`) at `-j4`, 2,003 s, max RSS 1,583,952 KiB, memory.peak 4.59 GB (incl. file pages). D-class pairs (class>0, same type, different bytes, one leaf frame):

| disc | leaves | leaves with a D pair | D-contain | D-overlap | D-rot |
| --- | ---: | ---: | ---: | ---: | ---: |
| G AU `0c22b266` | 3,954,165 | 377,083 | 17,769,567 | 1,087,605 | 2,205 |
| G Perth `5b86d33e` | 1,949 | 1,571 | 1,480,848 | 35,692 | 113 |
| R `8c2d2027` (whole frames) | 482,473 | 14,657 | 5,500 | 40,888 | 9 |

- G AU by type: L0/288 carries 17,569,839 contain + 996,128 overlap + 2,190 rot (98.5 % of all D pairs, 18,568,157 / 18,859,377; review 1 finding 5 — superseded by the review-fix rerun: 18,568,441 / 18,859,711 = 98.5 %); R has **no type-288 D pair at any level**. Next (post-review-fix values, committed json): L0/291 G 135,071 / 66,195 vs R 1,627 / 21,247; L0/321 G 41,794 / 6,999 vs R 403 / 78; L0/578 G 11,605 / 15,729 vs R 48 / 292. (The table above is the pre-review-fix run; post-fix totals in Review 1.) Per level / type counts in `dclass_{au,perth,R}.json`, first 20,000 example rows per class in the tsv.gz.
- **Reading:** G's D-classes exceed R by orders of magnitude and are concentrated in type 288 (the F6 catch-all→288 type, Cody-held, out of scope here). No D-class RC is attempted in this plan: Phase 2's D-class RC requirement is routed to Design with the Phase 2 stop below.

### P1 artefacts (committed, `p10_bg_dedup/`)

- `r_correspondence.{tsv.gz,json}` (sample; pre-fix `fe38eabb…`, post-review-fix `ccb1e9f9…` / json `7c0b5524…`, runs A == B); `r_correspondence_national.tsv.gz` (`867e12ce…`) / `.json` (`a71fb404…`); `r_census.tsv.gz` (`c8ef0707…`) / `.json` (`d4a97b63…`) (run B byte-identical); `a1_verdicts.json` (`3a307345…`, run B byte-identical); `dclass_{au,perth,R}.{json,tsv.gz}` (tsv.gz pre-fix `d8b579f4…`, `375d42ca…`, `b7110e08…`; post-review-fix `8c67f7f7…`, `a33171c0…`, `0bfc8772…`, runs A == B); with P1a's census and `sample.json`.
- `residuals.tsv`: R-G5-4-a-1 → discharged-plan-68 (222 rows / 8 groups build:eo_bg_stitch); R-G5-6 text corrected (R holds 486 duplicate classes; plan 63's R count was a reader artefact) and the correspondence / D-class results added; status unchanged (blocks-phase3, Design).
- Ledger `docs/plans/56-cross-phase-rss-profile/ledger/bg_dedup_plan68.json` + SUMMARY rows.

### P1 + P2 scratch receipt (17:20–17:21 AEST)

- Before: `du -sb output/scratch-68` = 619,645,918 (sc_au 567,431,091; perth disc 31,538,911; sc_perth 16,722,922; outputs, logs, a1win). Worktrees `../open-pajero-maps-68-sidecar` (86,819,909 B, only the plan-63 sidecar patch applied) and `../open-pajero-maps-68-33006aa` (10,164,202 B, same).
- Kept items verified `cmp`-equal to their committed copies before deletion (8 outputs + `rules.json`).
- After: `output/scratch-68` gone (no `keep/`); both worktrees removed (`git worktree remove --force` + `prune`; `git worktree list` has no `68-` entry); `/tmp/p68*` probe scripts removed; no maps-heavy scope of mine; `TMPDIR` / `KW_SIDECAR_DIR` unset in my shell.
- Untouched: `.heavy.lock`, `scratch-45` / `scratch-50` (spool overlay) / `scratch-53` (oracle discs), `extract_timing/spool`, R, `.venv-rp`, other plans' scratch and worktrees.
- `df -h /home`: 324G size, 298G used, 9.5G avail (97 %).

## Phase 2 — Dedup rule; D-class RCs (STOPPED for Design, 17:21 AEST)

- `p10_bg_dedup/rules.py` → `rules.json` (pre-fix `a4d3d4ae…`, post-review-fix `4f1a4736…` — only the input sha changed; run A == run B byte-identical; light, 33 MB RSS, 0.07 s; run without the wrapper because the heavy lock was held by other plans' jobs and this read of two committed tsv.gz files is not heavy work).
- Candidates: keep-first, keep-last, keep-own-cell-first, merge-sources, drop-all. Design set = R-one-byte ∪ R-one-geom classes: **0 in derivation, 0 in holdout** (and 0 nationally among the 2,164 framing-equal classes). No rule can reach "100 % on derivation and holdout" on an empty set, so none is accepted.
- Measured only (not an acceptance): on the comparable set (R-absent + R-merged + R-other), drop-all matches R in 125/135 derivation and 141/149 holdout classes (R-absent); merge-sources 1/135 and 0/149; keep-* 0.
- **Outcome: "no rule accepted" — the plan stops for Design** (Phase 2 outcome text). D-class RCs not attempted (see P1d reading). Phase 3/4 not started; no encoder change, no oracle change.


## Reader re-audit (Design ruling 2026-10-09 17:23; done 17:51 AEST)

Question: which committed claims read R through plan 63's truncating cut `frame[:U16(frame, 0) * 2]` (`p7_producer_tie/provenance.leaf_all_records` callers), and which conclusions change when R is read whole. Tool `p10_bg_dedup/reader_audit.py` (modes `g`, `p64`); one wrapper run (flock + 12G), max RSS 317,276 KiB / memory.peak 4.04 GB incl. file pages, 444 s.

Every committed caller of the cut (`rg "U16\(.*, 0\) \* 2"` over `historical_bg/` and `parser/tools/`):

| Plan / tool | Disc(s) cut | R read? | Claim | Re-check | Changes? |
| --- | --- | --- | --- | --- | --- |
| 63 `dup_census.py` | R, 013586b5, 0c22b266 | **yes (cut)** | "R holds byte-identical duplicates in 0 leaves" (`dup_census_R.json`) | `r_census.py` whole-frame: R holds **486 classes in 258 leaves**; the cut parses 0 of R's 1,315,200 background records | **Yes** — already corrected in R-G5-6 by plan 68 P1 |
| 63 `provenance.py` (P2 provenance, rules, G1/G2 gates) | 013586b5 windows only | no | producers per copy; rule 537/537 + 546/546; R-G5-1-a / R-G5-2-a discharged (4,612 build) | `reader_audit g` on 013586b5: cut == whole for **3,954,156 / 3,954,156** frames (11,601,627 records), 0 length-word overruns | No — discharges stand |
| 64 `trace.py` / `stage.py` / `classify.py` | R, 013586b5, 4ed9cd80, 0c22b266 | **yes**: geometry via plan 48 `r_parent` (whole entry); wire bytes via the cut | "R has 0 type-288 polygons in each of the 23 leaf cells"; H3 23/23 | `reader_audit p64`: on R, 23/23 cells decode (whole) == whole-frame wires record-for-record (105 records, types and classes equal); the cut yields 0 wires (so `trace.json`'s R `wire` fields are null, unused by any verdict); type 288 on R: **0 decoded, 0 in whole wires** (all classes); G discs: cut == whole on 4ed9cd80 3,954,159/3,954,159 and 0c22b266 3,954,165/3,954,165 | No — claim and H3 verdicts stand |
| 68 `census.py`, `a1.py` | 0c22b266, Perth, 013586b5 windows | no | live census 338,565; a1 222 build | G cut lossless (above) | No |
| 68 `r_census.py`, `r_corr.py`, `dclass.py --whole` | R | whole | R census / correspondence / D-classes | already whole-frame (R frame hash `fnv` in `r_corr` is computed on the cut but used only for G sidecar matching) | No |

- On G discs the length word is the frame length, so the cut is lossless there; every G-side claim of plans 63 / 64 / 68 stands.
- The only changed conclusion is plan 63's R duplicate count (0 → 486), already carried by R-G5-6 (to be split per the ruling).
- Earlier R readers (plan 48 `RReader` / `r_parent` / `decode_parcel`, used by plans 44–62) read the whole leaf entry (`length = entry.size * ls`) and are not this cut.
- Outputs committed: `reader_audit_p64.json`, `reader_audit_g_{013586b5,4ed9cd80,0c22b266}.json`.

## Review 1 (Codex, read-only, 17:28 AEST): FIX → fixes

1. **Medium — `r_corr.near()`** missed crossing rings whose vertices are all far from the other's edges (perpendicular rectangles sharing 16 raw²). Fixed: `rings_cross()` edge-intersection test before the vertex distances.
2. **Medium — `dclass.py` D-contain** tested only the direction picked by shoelace area (an even-odd bowtie has ~0 signed area). Fixed: containment tested in both directions.
3. **Medium — Phase 1 closed without unit tests or double runs** for the G censuses, national correspondence and D-class censuses. Added `parser/tests/test_p10_bg_dedup.py` (7 tests; the two regression tests fail on the pre-fix code, pass after); double runs below.
4. **Medium — "never" overstated** — qualified to "the committed sample and the 2,164 national framing-equal classes" here, in `synthesis.md` and in OVERVIEW.
5. **Low — 98.9 %** → 98.5 % (L0/288 share of all G AU D pairs).

**Review-fix rerun** (`output/scratch-68/rerun/rerun.sh`, one wrapper run under flock + 12G; queued 17:51, lock acquired ~18:08 behind other lanes' jobs):
- Sidecar worktree `../open-pajero-maps-68-sidecar` (`c5d329c` + plan-63 patch) re-created; sidecar AU and Perth encodes sha256 `0c22b266…` / `5b86d33e…` (output-neutral, again).
- Census run B (AU, Perth): json (minus `wall_s`) and tsv.gz byte-identical to the committed run A.
- Sample correspondence A == B (tsv.gz byte-identical). Versus the pre-fix file, **only R-alias rows' measured `geom_class` changed** (15 alias rows absent → R-other via the crossing test; 7 alias rows' `near` detail); the classes that score (non-alias) are unchanged: R-absent 266, R-merged 1, R-other 17, R-noncomparable 2,188 (alias 1,497, type-set 691). Alias geometry classes now: absent 580 (was 595), type-set 674, other 243 (was 228).
- National correspondence A == B and byte-identical to the committed pre-fix file (2,164 framing-equal: absent 541, type-set 1,609, other 13, merged 1, one-* 0).
- `rules.json` re-scored on the new sample file: unchanged outcome and scores (drop-all 125/135 and 141/149; no rule accepted).
- D-class censuses A == B (json minus `wall_s`, and tsv.gz). Totals after the fix: G AU contain 17,769,942 / overlap 1,087,564 / rot 2,205, leaves with a D pair 377,088 (was 17,769,567 / 1,087,605 / 2,205 / 377,083); Perth 1,480,892 / 35,691 / 113 / 1,571 (was 1,480,848 / 35,692 / 113 / 1,571); R 5,531 / 40,883 / 9 / 14,671 (was 5,500 / 40,888 / 9 / 14,657). L0/288 share of G AU D pairs 98.5 %; R still has no type-288 D pair.
- The drop-all mismatches are all non-288: derivation 10 = R-other 7 × type 321 + 2 × 289 + R-merged 1 × 321; holdout 8 = R-other 8 × 321. National framing-equal non-matches: R-other 11 × 321 + 2 × 289, R-merged 1 × 321.

## Plan close (Design ruling 2026-10-09 17:23)

- **Closed at Phase 2 as a findings plan.** Phase 3 (encoder dedup on windows) and Phase 4 (successor oracle) are **cancelled**: no candidate rule can be accepted (0 R-one-byte / R-one-geom classes to score, in the sample and in all 2,164 national framing-equal classes), and Design ruled against implementing drop-all — the type-288 bulk is a content question (F6 catch-all, Cody-held) rather than an emission-dedup one. No encoder change, no oracle change; `0c22b266…` / `5b86d33e…` stay in force.
- **Phase 4 gate text, rewritten for the record.** The draft's Phase 4 gate ("`dup_census.py` on the successor reports **0** leaves with byte-identical same-type class>0 duplicates at every level") is withdrawn: R itself holds 486 such classes in 258 leaves (plan 63's 0 was a reader artefact), so "0 duplicates" is not R parity. Any future successor gate for this class reads: *G duplicate classes where R holds no copy → 0 (per R-G5-6-a / -b remedy), and R's own duplicate classes (R-G5-6-c) reproduced where G and R frames are comparable; neither side measured through the truncating cut.*
- **Recorded process deviation (accepted by Design):** the Phase 2 scoring read (`rules.py`, 33 MB RSS, 0.07 s, two committed tsv.gz inputs) ran without the flock wrapper while other lanes held the heavy lock. All heavy runs stayed under flock + `run_heavy_python.py --memory-max 12G`.
- **R-G5-6 split** (residuals.tsv, OVERVIEW):
  - **R-G5-6-a** — G duplicate (338,038 classes) and different-bytes same-type (98.5 % of 18,859,711 D pairs) classes on L0 type 288, where R has nothing or another type (sample: every comparable 288 class is R-absent; none R-other / merged). Content row, `blocks-phase3`, remedy owner **Cody** (held with F6 and the plan-64 open-ways finding: 17/17 plan-64 producers are open OSM ways closed and typed 288 by the L0 catch-all).
  - **R-G5-6-b** — G duplicate classes not on type 288: **527** (L0 289 17, 290 12, 291 364, 321 110, 322 5, 578 10, 640 3; L2 290 6), plus the drop-all mismatches (derivation 10/135, holdout 8/149; all types 321 / 289). RC owed; owner Design.
  - **R-G5-6-c** — R's own 486 duplicate classes (258 leaves; L0 291 197 / 321 9 / 640 45, L2 291 189 / 321 13 / 640 26, L4 321 5, L6 321 2); none coincides with a G duplicate class. Whether and how many G reproduces is not measured; RC owed; owner Design.
- R-G5-4-a-1 stays discharged (plan 68 Phase 1, 222 build).


## Review 3 (OpenCode DeepSeek Flash, read-only, seat change 19:21; 19:41 AEST): LAND

All five review-2 findings verified resolved (P4 gate withdrawn/rewritten in this record; pre/post-fix hashes match git blobs and committed files; per-type figures match `dclass_{au,R}.json`; ledger peak 11,189,379,072 B / 4,967.9 s; record path cited by residuals/ledger exists). Non-blocking: (1) national-correspondence and r_census `.json` hashes were paired with the tsv.gz hash — split above (`a71fb404…`, `d4a97b63…`); (2) provenance said `output/scratch-68/` deleted while `review/` remained — now true (receipt below). Paths under `output/scratch-68/` cited above are historical (scratch deleted).

## Close-out scratch receipt (2026-10-09 19:44 AEST)

- Before the close-out: `output/scratch-68` = 621,556,171 B (`rerun/` 620,057,396; `review/` 1,498,775; `audit/` empty), plus worktree `../open-pajero-maps-68-sidecar` 86,819,909 B (re-created for the rerun; `git apply -R --check` confirmed it held only the plan-63 sidecar patch).
- Removed: the worktree (`git worktree remove --force` + `prune`), `rerun/`, empty `audit/`, then `review/` (1,504,230 B at deletion, after review 3).
- After: `test ! -e output/scratch-68` ✓ (no `keep/`); `git worktree list` has no `68-` entry; no `/tmp/p68*`; no maps-heavy scope of plan 68 (the one running scope is plan 67's P1 census); `TMPDIR` / `KW_SIDECAR_DIR` unset; committed outputs checked by sha256 against the rerun outputs before deletion. `df -h /home`: 324G size, 298G used, 9.3G avail (97 %).
- Not touched: `.heavy.lock`, other plans' scratch (incl. scratch-32 pins), spool of record, R, oracle discs, `.venv-rp`.
