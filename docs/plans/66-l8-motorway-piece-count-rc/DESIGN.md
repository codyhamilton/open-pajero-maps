---
design_id:
---

# R-G9-3-b piece-count residual: why G emits 2,979 motorway pieces where R has 128 dc12 links at L8 — proven RC, then fix or proof

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Cody's hard bar as restated 2026-10-08: every deviation needs a proven root cause; no waivers; carried is not closed; never pick an arbitrary rule and call it proven.

Design brief (2026-10-08): draft a design for the undrafted Design-owned carried row R-G9-3-b's piece-count residual, with a proven-RC path and gates that carry no "optional" wording.

Master direct. Heavy work under flock + `run_heavy_python.py --memory-max 12G`, encode `-j4`, K1 ≤ `-j6`. **Out of scope and untouched:** L8 road *selection* — which OSM classes are admitted at L8 (R-G9-3-c, Cody) — plus F6 / kind-order and roads preference (Cody). Assigned Execute instance: OpenCode DeepSeek Flash.

**Scratch-rule note (Design, 2026-10-09):** Cody's standing rule added: every phase outcome now includes a scratch receipt with named keep / delete lists (see "Scratch hygiene" and each phase). No other change to this draft.

## Problem

**Ground (GitHub `origin/master` `4bb96f0` (plan 65 close-out; rows 54–57 unchanged from `8498eec`), read-only on the box, 2026-10-08):**

1. **The row.** `residuals.tsv` R-G9-3-b (line 54): at L8 (7,4), G has 2,979 dc12 pieces vs R's 128 dc12 links (929 R links in total).
   - Plan 52 proved why the *short* pieces exist: extract-emitted short motorway ways. `mechanism = extract-short-motorway-ways`; 1,089 pieces have `npts==2`; each piece is a unique `way_id`; p50 ≈ 46 m.
   - It also proved the shrink drop of 308 2-vertex stubs loses no R-quantum geometry: dc12 coverage is 100% at 1 parent-raw, against a 0.95 threshold committed before measuring.
   - What is still unexplained is the piece-count inflation itself.
   - Owner text: "Design (piece-count residual; **optional** generalisation successor)"; blocking `maps-parity-carried`.
2. **Evidence at tip** (`trim_r_parity/l8_frag/remeasure.json` sha `7c969a6e…`, `frag_mech.json` sha `920b8324…`, measured on `aeae426c`):

   | Fact | G | R |
   | --- | --- | --- |
   | Links / pieces in parent (7,4) | 2,979, all dc12, road_type 0 | 929 = 801 dc10 (road_type 2) + 128 dc12 (road_type 0) |
   | Spool roads behind G | 3,281 = 3,281 unique `way_id`, 1 piece per way | — |
   | 2-vertex links | 781 | 587 (all classes) |
   | Division of the parent | leaf paths (19, 0…15): 4×4; populated 2 / 3 / 7 | leaf paths (19, 0…3): 2×2; all 128 dc12 links in leaf 1 |
   | Coverage | — | R dc12 covered by G at 1 parent-raw: 100% (3,049.9 / 3,049.9 parent-raw) |

   - **G pieces correspond one-to-one to OSM ways.** R's dc12 links are far fewer, so R either aggregates ways into links, admits less motorway geometry as dc12, or both.
   - **Reverse coverage was never measured:** how much of G's dc12 length has R dc12 within 1 parent-raw.
   - **The division mismatch is coupled to this:** G 4×4 vs R 2×2, with G leaf 3 frame bytes at 131,072. It is an observable consequence that must be re-checked once the piece count changes.
3. **Measurement is on `aeae426c`.** Live oracle is `0c22b266…` (plan 53: 565 changed cells, 553 at L0 plus halo). L8 (7,4) is not shown to be unchanged. Phase 1 re-measures on live.
4. **The inflation is accepted nationally by calibration, not explained.** `parser/refdata/selection.json` L8 note: "R links 7,663. motorway = 14,004 ways (1.83x, near ceiling)". That compares G motorway *ways* with R links of *all* classes. R dc12 national is not in the note, so the dc12-for-dc12 ratio nationally is unknown. `parser/refdata/harness.json` `count_ratio` envelope is [0.5, 2.0]. Being inside a calibration envelope is not a parity proof. The selection `_comment` itself calls selection "a stopgap for count parity". This plan does not change the envelope or the selection.
5. **Only one parent is measured per link.** Per-parent dc12 inflation is measured only at (7,4). Whether a rule generalises is unknown. No plan-52 generator script is committed: only JSON under `l8_frag/`, and `remeasure.json` names `output/scratch-50/G_new`.

## Solution shape

### Domain: national dc12 link census on R and live G

- **Owns:** `triage/trim_r_parity/l8_piece_count/` (new): a committed generator + census over every L8 parent with R dc12 links (and the same parents on `0c22b266`).
- **Contract:**
  1. Per parent:
     - R dc12 link count, vertex histogram, per-link parent-raw length, endpoint degree (how many dc12 links meet at each endpoint);
     - G dc12 piece count, the same statistics, and `osm_way_id` and highway tag (`motorway` vs `motorway_link`) through the spool;
     - forward coverage (R by G) and reverse coverage (G by R, all R classes and dc12 only) at 1 parent-raw;
     - division topology on both discs.
  2. Re-measures (7,4) on `0c22b266` and states whether plan 52's counts still hold.
  3. Deterministic; generator committed, so no scratch-only JSON.
- **Non-goals:** dc10 / other classes (selection is Cody's); any build change.

### Domain: piece-count root cause (rule derivation with holdout)

- **Owns:** a scored table of candidate mechanisms, each defined before scoring, and an accepted RC or a per-parent named RC.
- **Contract:**
  1. **Candidates (at least):**
     - **C1 way chaining:** R link = maximal chain of consecutive dc12 ways that join at a node of degree 2 with equal link attributes (road_type, flags, oneway, route number).
     - **C2 link-class treatment:** `motorway_link` is excluded from dc12, or emitted in another class, in R.
     - **C3 carriageway representation:** R carries one centreline where OSM has dual carriageways.
     - **C4 generalisation:** R merges or drops pieces below a length or vertex threshold.
     - **C5 source drift:** G motorway geometry absent from R in every class is post-DVD (2007) network.
     - **C6 division-coupled split:** links are cut at G's finer leaf boundaries.
  2. **Acceptance bar.** Pre-commit thresholds before scoring: count error, per-link geometry Hausdorff ≤ 1 parent-raw. A candidate rule (or a fixed combination) is accepted only if it reproduces R's dc12 link count and per-link geometry 100% on the derivation parent(s) **and** 100% on a holdout set of parents chosen by fixed hash before scoring.
  3. **C5 needs per-way evidence** that the geometry post-dates the DVD era: an OSM `start_date` / `opening_date` tag, or OSM full history (first version after 2007) for the way. It also needs reverse coverage showing R has no road of any class within 1 parent-raw. Without both it is not accepted.
  4. A mechanism that would change **which OSM classes reach L8 or their display class** (e.g. C2 showing R maps `motorway_link` to dc10 or omits it) is a selection or mapping question. The evidence is published, and the remedy goes to Cody via Design. This plan does not implement it.
  5. No accepted rule → each parent stays with its own named RC from the scored evidence. No "optional", no carried end state.
- **Non-goals:** threshold tuning after scoring; nearest-match heuristics.

### Domain: remedy and residual update

- **Owns:** for a G-side mechanism (C1 / C3 / C4 / C6) the extract or encoder change; for C5 the proof record; `residuals.tsv` R-G9-3-b.
- **Contract:**
  1. **G-side fix.** Lands in the stage the RC names, with tests. That is the spool extract `parser/osm_to_parcel_geometry.py` (roads are split into `(osm_way_id, ordinal)` chains there) or the encoder `parser/kiwiw/_e2.c`. A successor oracle from a full AU `-j4` encode must show:
     - confined diff vs `0c22b266…` (changed set listed);
     - R-DVD no-worse on every changed L8 parent (dc12 count and both coverages);
     - (7,4) dc12 count equal to R's within the pre-committed bar;
     - division topology re-checked;
     - Perth checked;
     - K1 failing 0; close gates a/b/c.
     
     Design accepts before promotion.
  2. **C5.** The row is discharged as proven source drift only with the per-way evidence above for every unmatched G way.
  3. **Selection or mapping outcome** (contract item 4 above): the row becomes an exact child whose RC is proven and whose remedy owner is Cody. It is not closed by this plan, and that is stated without "optional".
  4. `residuals.tsv` R-G9-3-b owner text is replaced, removing "optional generalisation successor".
- **Non-goals:** R-G9-3-c volume; F6 / kind-order / roads preference.

### Memory guardrails (all phases)

- Serial under `flock output/.heavy.lock` + `run_heavy_python.py --memory-max 12G` (MemorySwapMax=0).
- Census streams per L8 parent with spool caches cleared per batch (plan 57 levers).
- Full AU encode at `-j4` with the `bench_build.py` tree sampler (plan 58: AU tree ~15.3 GB-class).
- OOM or cap trip → stop_for_design with peak. Peaks go into the plan-56 ledger as `ledger/l8_piece_count_plan66.json` + SUMMARY row.

### Scratch hygiene (all phases; Cody standing rule, 2026-10-09)

- **Rule (Cody):** Execute cleans its scratch after every phase, keeping only what the ledger or the next phase needs. **A phase is not done until its scratch is cleared.** The receipt below is part of every phase outcome.
- **This plan's scratch:** `output/scratch-66/`, any git worktree this plan adds, any temp dir its runs create (named in the run log), and the wrapper's cgroup scopes. Nothing else.
- **Never deleted by this plan:** `output/.heavy.lock` (shared flock file); other plans' `output/scratch-*` (some are pinned evidence, e.g. `oracle_chain/pin_contract.py` pins `output/scratch-32/…`); the spool of record; the R (DVD) image; the disc in force and earlier oracle discs; `.venv-rp`.
- **What may be kept:** committed artefacts first. Ledger rows carry the peak fields copied from the wrapper log, so the log itself is not kept. Anything the next phase needs that cannot be committed goes under `output/scratch-66/keep/`, listed with path, bytes and sha256, and is deleted at the end of the phase that consumes it.
- **Receipt** (`scratch_receipt` in the plan note, one per phase):
  1. `du -sb output/scratch-66` before cleanup and after;
  2. after: `test ! -e output/scratch-66` (gone), or `ls -A output/scratch-66` shows only `keep`, with its contents listed;
  3. `git worktree list` shows no worktree from this plan (after `git worktree remove` + `git worktree prune`);
  4. every temp dir named in the phase's run logs is gone, and no wrapper scope from the phase is still running;
  5. kept list checked: every kept path exists, committed paths appear in `git ls-files`, `keep/` items match their recorded sha256.
- A missing or failing receipt means the phase is not done. The final phase ends with `output/scratch-66` gone.

## Decisions

1. Plan number **66**. Master direct. Three phases: census; RC derivation; remedy / residual.
2. Derivation parent = (7,4) plus any parents the census shows with the same pattern. The holdout is fixed by parent hash before scoring.
3. Anything that changes L8 class admission or class→dc mapping is routed to Cody, never implemented here.
4. Tip `4bb96f0`; live oracle `0c22b266…`, Perth `5b86d33e…`.

## Assumption ledger

### Assumption 1

- **Question:** Is piece-count inflation separable from R-G9-3-c's selection question?
- **Answer chosen:** Yes for dc12. R's 128 dc12 links and G's dc12 pieces are compared class-for-class. dc10 is not touched.
- **Rationale:** `remeasure.json` dc split; plan 52 proved b and c by separate mechanisms.
- **If wrong:** if the census shows R carries some OSM motorway geometry as dc10, contract item 4 routes it to Cody with the evidence.

### Assumption 2

- **Question:** Does OSM history evidence for C5 exist offline?
- **Answer chosen:** Unknown. The spool PBF (`australia-260824.osm.pbf`) is a snapshot without history. Tags like `start_date` exist on some ways only.
- **Rationale:** `docs/provenance.md` L211–216.
- **If wrong / unavailable:** C5 cannot be accepted, and those ways stay with a named open RC.

### Assumption 3

- **Question:** Does live `0c22b266` change L8 (7,4)?
- **Answer chosen:** Probably not (plan 53's diff is L0 + halo), but it is re-measured, not assumed.
- **Rationale:** `l0_degen/cells_aeae426c_to_0c22b266.tsv`.
- **If wrong:** Phase 1 records the change and plan 52's figures are restated.

## Open questions

1. Where a cross-way chaining step would belong: `osm_to_parcel_geometry.py` (today one chain per way, `_Chain.ordinal`) or the encoder. Refine locates it before Phase 3.
2. Minimum holdout size, set from the Phase 1 census count of parents with R dc12.

## Phases

### Phase 1 — National dc12 census on live G and R

- **Outcome:** `l8_piece_count/census.json` (+ committed generator) covers every L8 parent with R dc12. (7,4) is re-measured on `0c22b266`, with plan 52's counts confirmed or restated. Forward and reverse coverage, per-link statistics, way / tag join and division topology are recorded. Double run identical. Peak in the 56 ledger.
- **Scratch cleared (part of the outcome):** keep `l8_piece_count/census.json`, generator + unit test, `docs/provenance.md` entry (committed); 56-ledger row. Phase 2 reads only the committed census. Delete `output/scratch-66/` contents: decoded R and G L8 frames, spool way / tag join tables, double-run copies once compared, wrapper logs once copied. Proof: the phase's `scratch_receipt` (see "Scratch hygiene").
- **Surfaces:** `triage/trim_r_parity/l8_piece_count/`; `parser/tests/` (generator unit test); `docs/provenance.md`.
- **Approach:** known. **Depends on:** none. **Refine:** skipped.

### Phase 2 — Piece-count RC proven or named per parent

- **Outcome:** `l8_piece_count/rc_table.json` scores C1–C6 (and any added candidates defined before scoring) on derivation and fixed holdout. Thresholds are committed before scoring. Exactly one accepted mechanism is stated with its pipeline stage, or each parent carries its own named RC. Selection / mapping findings are flagged for Cody with evidence.
- **Scratch cleared (part of the outcome):** keep `rc_table.json`, the thresholds and holdout hash list committed before scoring (committed). Delete candidate-rule outputs, chained / generalised geometry intermediates, scoring shards. Proof: the phase's `scratch_receipt` (see "Scratch hygiene").
- **Surfaces:** `l8_piece_count/`; `output/scratch-66/` (gitignored).
- **Approach:** open (the chaining / generalisation model is not settled; the 100% + holdout bar is the yardstick). **Depends on:** Phase 1. **Refine:** candidate definitions + holdout draw.

### Phase 3 — Remedy landed or proof recorded; residual updated

- **Outcome:** One of three ends, each with `residuals.tsv` R-G9-3-b updated (no "optional"):
  - G-side fix landed with tests and a Design-accepted successor oracle (confined diff vs `0c22b266`, R-DVD no-worse, (7,4) dc12 count within bar, Perth, K1, close gates), with the row discharged;
  - proven source drift with per-way evidence, with the row discharged;
  - an exact child with proven RC and Cody as remedy owner (selection / mapping), not closed by this plan.
- **Scratch cleared (part of the outcome):** keep the fix + tests, `successor_oracle_<sha>.json`, the promoted disc at the disc-in-force path (outside scratch), a promoted spool at the spool-of-record path, `residuals.tsv`, README / causes pointer, ledger row. Delete the whole `output/scratch-66/`: non-promoted candidate encodes and spools, AU / Perth build trees, K1 dumps, decoded discs, any `keep/`. Proof: the phase's `scratch_receipt` (see "Scratch hygiene").
- **Surfaces:** per RC — extract / `_e2.c` + tests + `successor_oracle_<sha>.json` + OVERVIEW oracle line; `residuals.tsv`; `causes_residual.md` / `l8_frag/README.md` pointer.
- **Approach:** known (per accepted RC). **Depends on:** Phase 2. **Refine:** only for a G-side fix.

## Provenance

- Tip GitHub `origin/master` **`4bb96f0`** (fetched 2026-10-08; drafted against `8498eec`, re-checked at `4bb96f0`). Sources: `parser/refdata/selection.json` L8 calibration note; `parser/refdata/harness.json` envelope; `residuals.tsv` lines 54–55; `docs/plans/52-l8-road-fragmentation-underselect.md`; `trim_r_parity/l8_frag/{README.md, frag_mech.json (920b8324…), remeasure.json (7c969a6e…), underselect/volume_table.json}`; `docs/plans/42-encoder-trim-r-parity.md`; plan 53 record (oracle chain); plan 58 record (AU tree peaks).
- Siblings: **67** (R-G9-3-d-rem); R-G9-3-c stays with Cody.
- Rejected: implementing L8 selection or class-mapping changes; accepting a rule without a holdout; C5 without per-way evidence; "optional" or carried end states.
- Box draft only. No commit from Design.
