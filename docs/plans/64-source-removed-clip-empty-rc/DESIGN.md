---
design_id:
---

# Empty-clip "source-removed" rows (R-G5-1-b 50 + R-G5-4-a-2 32 + R-G5-4-b-1 545): why the producer clips empty on d35b565 — prove the cause per group, fix a defect, or prove source absence

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Cody's hard bar as restated for this work (2026-10-08): Maps is complete only when end-to-end generation matches the original DVD in every verifiable aspect. Every deviation needs a proven root cause. No waivers, and carried is not closed. Never pick an arbitrary rule and call it proven.

Design brief (Execute hand-off after plan 46): give R-G5-1-b (50 rows / 1 group, "source-removed", producer clip empty on `d35b565`) a direction. Prove why the clip is empty: source data drift vs the DVD era, a clip/extract defect, or a wrong producer. Find the producer feature in the extract and in the original source, compare against the R bytes, and fix it if it is a defect. If it is genuine source absence, state the exact proof needed: the feature is absent from the input source, and R's bytes cannot be produced from any available input. No waiver.

Master direct. Heavy work under flock + `run_heavy_python.py --memory-max 12G`, encode `-j4`, K1 ≤ `-j6`. Oracle change only through the successor-oracle discipline (plans 48 / 50 / 53) and a Design accept. No plan 04 P4–6, no 3-90, no reseat 170 / 3-16 / 3-17. No F6 / kind-order / roads / L8 work. Assigned Execute instance: OpenCode DeepSeek Flash.

**Scratch-rule note (Design, 2026-10-09):** Cody's standing rule added: every phase outcome now includes a scratch receipt with named keep / delete lists (see "Scratch hygiene" and each phase). No other change to this draft.

**Scope revision (Design, 2026-10-09 ~14:45 AEST, tip `61d2fe8`).** Plan 62 closed (`b889c2e`) and routed two children here: **R-G5-4-a-2** (32 rows / 1 group) and **R-G5-4-b-1** (545 rows / 21 groups), same mechanism as R-G5-1-b (producer in the candidate set, its `d35b565` clip into the leaf empty). Scope is now **627 rows / 23 groups**, each decided by the same five-way test H1–H5. Plan 63 closed (`61d2fe8`), so its `33006aa` sidecar is committed and the fallback is no longer needed. The Intent above is unchanged; see `REVISION-NOTE.md`. Pre-revision copy: `64-source-removed-clip-empty-rc.bak-2026-10-09/`.

## Problem

**Ground (GitHub `origin/master` `61d2fe8`, read-only on the box, 2026-10-09; items 1–5 first read at `8498eec` and unchanged at `61d2fe8`):**

1. **The row.** `residuals.tsv` R-G5-1-b reads: 50 background_boundary rows / 1 group (0,1750,594,(598,3)), shape 171, type 288. The unique-byte producer (1751,594,16) on `33006aa` clips into the leaf as **empty** (sz 0) under `d35b565`, "so the build-side record cannot be checked". `verdicts.tsv.gz` (`ca4a555a…`) carries the same: `extra = {"producer":[1751,594,16],"sz":0}`; dump fields depth 1, p0 598, p1 3.
2. **The 50 rows** are vertices 26–75 of shape 171, and all of them lie on the leaf frame: 34 on x=0, 3 on y=0, 13 on y=4096, in densified runs of about 124 raw units (Design Ground read of the verdict rows). The producer is homed in the east neighbour cell (1751,594), ring 16.
3. **"source-removed" is a misnomer for this row.** `phase23.py decide` has two `source-removed` branches. This row took the second one (L155–157): the ring **is** in the pinned spool's candidate set, and the `d35b565` exclusivity clipper returns sz ≤ 0 for it in this leaf. The first branch, "producer not in candidate set at decide", was not taken (`extra` has no `why`). The input source is present; the new encoder emits nothing from it here.
4. **The new-disc side is the EO stitch alone.** `4ed9cd80` = `33006aa` + `hop_3_14/eo_only.patch` (byte-equal `M_eo`, `docs/provenance.md` L855). On `4ed9cd80` the K1 background family fails 0 (`k1head_314` / `k1old_314`). So on the new disc the failing rows are gone. What is unknown is whether R (the DVD) agrees with what replaced them.
5. **Source chain.** Spool of record: `output/extract_timing/spool`, built from `australia-260824.osm.pbf` by `parser/osm_to_parcel_geometry.py` (`docs/provenance.md` L211–216). Spool background records carry no OSM element id (`parser/kiwiw/spool.py` columns `b_class, b_type, b_ncoords, b_mult, b_flags, b_nstored, b_label_len` + coords + label). Tracing ring 16 to OSM therefore needs an output-neutral provenance re-extract.
6. **Plan 62's children are now in scope** (`p9_r01_residual/transitions.json` `source_removed_groups`, sha `d51baafb…`; `redecide.tsv.gz` `9c47f1ef…`). Plan 62 re-decided plan 44's 469 `disagree_source_removed` rows under the plan-46 producer: 5 became build (U4F_RING: plan 44 Unit 4f took ring 0 in the home, the producer is ri 1; `u4f_probe.json`), 464 stayed source-removed, and 113 more arrived from other classes. Result:

   | Row | Groups | Rows | Old plan-44 class → source-removed | Type |
   | --- | ---: | ---: | --- | --- |
   | R-G5-1-b | 1 | 50 | (plan 46) | 288 |
   | R-G5-4-a-2 | 1 | 32 | source-removed 32 | 288 |
   | R-G5-4-b-1 | 21 | 545 | source-removed 432; outside@16 97 (RC3 found the far producer); skip_divided_leaf 16 (RC4) | 288 |

   - All 23 groups are **L0, type 288** (the L0 catch-all; plan 51), every one with `clip_size_d35b565` 0.
   - The 22 plan-62 groups have **16 distinct producers**; (1152,1422,0) feeds 4 leaves, (1248,910,0), (1248,980,0) and (1248,1444,0) feed 2 each. 14 groups sit in leaf columns ix 1248 (10) and 1152 (4).
   - Producer-to-leaf Chebyshev distance runs 0–26 cells (median 8). One group is in a divided leaf: (1738,570) path `1866.3`, producer ri 6105, 16 rows.
   - Several leaves are fed by one producer that runs a long way through the column. Whether these are long, thin rings whose piece in the leaf hugs or runs along the frame (as R-G5-1-b's 50 vertices do) is a Phase 1 fact, not assumed.

**Hypotheses this plan must decide between (exhaustive):**

| Id | Hypothesis | What would show it |
| --- | --- | --- |
| H1 | **Wrong producer:** the `33006aa` record was not emitted from ring (1751,594,16) (another ring, another type, or a non-ring path) | Emission provenance at `33006aa` names a different source |
| H2 | **Clip/stitch defect at `d35b565`:** the EO stitch drops a piece it should emit | A stage trace shows the piece lost at a named step, and R has type-288 coverage in the footprint that `4ed9cd80` / `0c22b266` lack |
| H3 | **Correct removal by the build:** the `33006aa` piece was an artefact (e.g. a frame-hugging or degenerate piece) and `d35b565` correctly emits nothing or re-emits the coverage through another record | `4ed9cd80` coverage of the footprint equals R's (byte or witnessed geometry), or R has no such coverage either |
| H4 | **Source drift vs the DVD era:** R has a record in the footprint that no available input can produce (or the OSM feature post-dates the DVD) | The genuine-source-absence proof below |
| H5 | **Extract defect:** `osm_to_parcel_geometry.py` maps or clips the OSM element wrongly into ring 16 | The re-extract shows ring 16 differs from the OSM element under the documented tag→type mapping |

## Solution shape

### Domain: producer and source trace

- **Owns:** `triage/historical_bg/p8_source_removed/` (new): trace evidence JSON for leaf (0,1750,594,(598,3)) shape 171.
- **Contract:**
  1. **Producer proof at `33006aa`, per group (23):** the emitting source of each group's `013586b5` shape, from plan 63's committed sidecar (`p7_producer_tie/sidecar/sidecar_33006aa.patch`; window build of each group's leaf cell, output-neutral gate vs `013586b5`). If it differs from the recorded producer, H1 holds for that group and it is re-decided with the plan-46 decide limb.
  2. **Extract trace, per distinct producer (17 = 16 + (1751,594,16)):** an output-neutral provenance re-extract of the producer's home cell from `australia-260824.osm.pbf` names the OSM element(s) behind the ring, with tags, the tag→type mapping that gave 288, and a coordinate comparison of ring vs element. A mismatch → H5 for every group that producer feeds.
  3. **R footprint read, per group:** R's (the DVD's) records in the leaf's cell whose geometry meets the shape's footprint: type, bytes, leaf. The same read on `013586b5`, `4ed9cd80` and live `0c22b266`.
  4. **Piece geometry, per group:** where the shape's vertices lie relative to the leaf frame (on-frame counts per edge, as Problem item 2 did for R-G5-1-b).
- **Non-goals:** a general source-tag sidecar in the production extractor (the provenance re-extract is a triage tool); cells outside the 23 groups.

### Domain: empty-clip cause at d35b565

- **Owns:** a stage trace of ring 16 through the `d35b565` clip pipeline into the leaf (clip → densify → round → EO stitch → merge/emit), using plan 48's output-neutral `eo_census` sidecar and a ring-id hook in a `d35b565` window build, plus the H2/H3/H4 decision.
- **Contract:**
  1. **Stage trace, per group:** name the first stage at which the producer ring's contribution to the leaf becomes empty, and why (input geometry, predicate, line in `_cenc.c` at `d35b565`). Window frames must be byte-equal to `4ed9cd80` (output-neutral gate). Groups sharing a producer and a stage may share one trace, but each group's verdict is recorded.
  2. **Coverage comparison** of the footprint between `4ed9cd80` / `0c22b266` and R:
     - equal, or R has no coverage either → **H3**;
     - R has coverage and G lacks it → **H2** if the stage trace shows a defect, otherwise **H4** candidate.
  3. **Genuine source absence (H4) is accepted only with both proofs committed:**
     - (i) **Absent from the input source.** No OSM element in `australia-260824.osm.pbf` whose tags map to the R record's type (via `osm_to_parcel_geometry.py`'s mapping) meets the footprint. This is a full-PBF bbox query, not a spool-only read.
     - (ii) **R's bytes cannot be produced from any available input.** No spool ring of any type, class or home meeting the footprint clips, under the live encoder, into a record byte-equal to R's or carrying its identity-bearing vertices. The enumeration is exhaustive over the bbox-meet set (RC3 FarHomes included) and committed per ring.
  4. Neither "source-removed" nor "carried" is an end state. Each of the 23 groups gets exactly one of H1–H5 with its proof; groups are never discharged by analogy with another group.
- **Non-goals:** changing K1 predicates; nearest-ring substitution.

### Domain: action and residual update

- **Owns:** `residuals.tsv` R-G5-1-b, R-G5-4-a-2, R-G5-4-b-1; when H2 / H5, the fix and its successor oracle.
- **Contract:**
  - **H1:** re-decide with the plan-46 decide limb under the proven producer → `build:eo_bg_stitch` or a named residual with RC.
  - **H3:** discharge with the coverage witness (`build:eo_bg_stitch (removed/re-emitted)` + R comparison).
  - **H4:** discharge as proven source absence with both proofs (contract 3).
  - **H5:** extractor fix with a re-extract diff confined to the named element(s), then a rebuild and K1 + R comparison.
  - **H2:** encoder fix in `_cenc.c`. Successor oracle from a full AU `-j4` encode, with a confined diff vs `0c22b266…`, R-DVD no-worse on every changed cell, Perth checked, and a Design accept before promotion. If the fix changes more than the footprint class of these 23 groups, it stops for a separate design rather than growing this plan.
  - The classifier (H1–H5 tests) is committed as a tool and run over all 23 groups (627 rows); its per-group output is the evidence for each row.
  - Each of the three rows is discharged only when all its groups have a proven outcome; otherwise it is replaced by exact children (per group) with proven RCs.

### Memory guardrails (all phases)

- Serial under `flock output/.heavy.lock` + `run_heavy_python.py --memory-max 12G` (MemorySwapMax=0). Window and full encodes at `-j4`; K1 ≤ `-j6`.
- Streaming re-extract: a bbox-filtered PBF pass, no whole-AU in-memory feature table. Spool caches are bounded and cleared.
- Any scan carries the plan-46 RssAnon watchdog (`--max-rss-mib`, 3072 MiB cap). A trip or OOM is a stop_for_design with the peak.
- Peaks go into the plan-56 ledger as `ledger/source_removed_plan64.json` + SUMMARY row. A full AU encode (H2 only) records the `bench_build.py` tree peak, as plans 56 / 58 do.

### Scratch hygiene (all phases; Cody standing rule, 2026-10-09)

- **Rule (Cody):** Execute cleans its scratch after every phase, keeping only what the ledger or the next phase needs. **A phase is not done until its scratch is cleared.** The receipt below is part of every phase outcome.
- **This plan's scratch:** `output/scratch-64/`, any git worktree this plan adds, any temp dir its runs create (named in the run log), and the wrapper's cgroup scopes. Nothing else.
- **Never deleted by this plan:** `output/.heavy.lock` (shared flock file); other plans' `output/scratch-*` (some are pinned evidence, e.g. `oracle_chain/pin_contract.py` pins `output/scratch-32/…`); the spool of record; the R (DVD) image; the disc in force and earlier oracle discs; `.venv-rp`.
- **What may be kept:** committed artefacts first. Ledger rows carry the peak fields copied from the wrapper log, so the log itself is not kept. Anything the next phase needs that cannot be committed goes under `output/scratch-64/keep/`, listed with path, bytes and sha256, and is deleted at the end of the phase that consumes it.
- **Receipt** (`scratch_receipt` in the plan note, one per phase):
  1. `du -sb output/scratch-64` before cleanup and after;
  2. after: `test ! -e output/scratch-64` (gone), or `ls -A output/scratch-64` shows only `keep`, with its contents listed;
  3. `git worktree list` shows no worktree from this plan (after `git worktree remove` + `git worktree prune`);
  4. every temp dir named in the phase's run logs is gone, and no wrapper scope from the phase is still running;
  5. kept list checked: every kept path exists, committed paths appear in `git ls-files`, `keep/` items match their recorded sha256.
- A missing or failing receipt means the phase is not done. The final phase ends with `output/scratch-64` gone.

## Decisions

1. Plan number **64**. Master direct. Three phases: trace; cause; act.
2. Uses plan 63's committed `33006aa` emission sidecar for the producer proof (63 closed `61d2fe8`; no fallback).
3. The R comparison is mandatory before any discharge. "Not failing on `4ed9cd80`" alone does not discharge, because removal can be a parity loss.
4. H4 needs both proofs. A missing proof leaves the row open with its RC named, not waived.
5. Tip ground `61d2fe8`. Live oracle `0c22b266…` / Perth `5b86d33e…`.
6. Scope 23 groups / 627 rows (R-G5-1-b + R-G5-4-a-2 + R-G5-4-b-1), one five-way test.
7. If an H2 / H5 fix moves the oracle, it lands before plan 68 starts its successor work, and 68 re-bases on the new sha.

## Assumption ledger

### Assumption 1

- **Question:** Is "source-removed" here a statement about the input source?
- **Answer chosen:** **No.** The ring is in the spool candidate set; the `d35b565` clip is empty (phase23 L155–157 branch).
- **Rationale:** `extra.sz = 0`, no `why`; `residuals.tsv` wording.
- **If wrong:** H1 or H5 surfaces in Phase 1, which tests it directly.

### Assumption 2

- **Question:** Is the R comparison feasible for one leaf without a full R-DVD census?
- **Answer chosen:** Yes. Plan 48 ran an R-DVD coverage check per changed cell (two L0 cells) before Design accepted `88bd7852`, and the K1 tooling reads R frames.
- **Rationale:** `docs/plans/48-eo-face-walk-decline.md` ("R-DVD equal coverage on both cells").
- **If wrong:** Execute names the missing reader. Phase 2 cannot pass without R; stop for Design.

### Assumption 3

- **Question:** Does this plan decide the R01 source-removed rows itself?
- **Answer chosen:** **Yes** (revised 2026-10-09). Plan 62 closed and routed R-G5-4-a-2 and R-G5-4-b-1 here (owner "Design → plan 64"). The old "469" figure is superseded by plan 62's re-decide: 32 + 545.
- **Rationale:** `residuals.tsv` R-G5-4-a-2 / R-G5-4-b-1; `transitions.json`.
- **If wrong:** n/a — one owner per row.

### Assumption 4

- **Question:** Do the 97 RC3 (far-producer) and 16 RC4 (divided-leaf) rows of R-G5-4-b-1 need a different test?
- **Answer chosen:** No. The same five-way test applies; H1 (wrong producer) is checked first for exactly these, since their producer was found by plan 46's fixes, not by plan 44.
- **Rationale:** plan 62 attribution (`outside@16 → source-removed` RC3 97; `skip → source-removed` RC4 16).
- **If wrong:** a group that fits none of H1–H5 stays open with a named new hypothesis and its evidence.

## Open questions

1. The exact R reader and leaf mapping for cell (1750,594) on the DVD (Execute names the tool plan 48 used for its R-DVD check).
2. Whether the PBF used for the spool of record is still on the host byte-identical (sha check in Phase 1; if not, the trace labels the substitute and H4 cannot pass on it).
3. Whether the long same-column producers (ix 1152 / 1248) are one feature class (e.g. long linear boundaries mapped to 288); Phase 1 item 2 answers it.

## Phases

### Phase 1 — Producer and source trace committed

- **Outcome:** `p8_source_removed/trace.json` states, **for each of the 23 groups:**
  - the proven emitter of the group's `013586b5` shape (plan 63 sidecar);
  - the producer ring's OSM element(s), tags and tag→type mapping, with the ring-vs-element comparison (per distinct producer);
  - the shape's on-frame vertex counts;
  - footprint records on R, `013586b5`, `4ed9cd80` and `0c22b266`.

  Plus the PBF sha. H1 and H5 are each decided true or false per group with evidence. Work already done for R-G5-1-b under the earlier scope stands and is reused. The peak is recorded in the 56 ledger.
- **Scratch cleared (part of the outcome):** keep `p8_source_removed/trace.json` (23 groups), trace driver, provenance re-extract helper, `docs/provenance.md` entry (committed); 56-ledger row. Phase 2 reads only `trace.json`. Delete `output/scratch-64/` contents: the `33006aa` sidecar worktree and its 23 window builds, osmium / PBF extract outputs for the 17 producer homes, decoded footprints from R, `013586b5`, `4ed9cd80` and `0c22b266`, wrapper logs once copied. Proof: the phase's `scratch_receipt` (see "Scratch hygiene").
- **Surfaces:** `triage/historical_bg/p8_source_removed/` (trace driver, provenance re-extract helper), `docs/provenance.md` entry.
- **Approach:** known. **Depends on:** plan 63 sidecar (committed). **Refine:** skipped.

### Phase 2 — Empty-clip cause decided

- **Outcome:** `d35b565` window stage traces (output-neutral gate passed) name, per group, the stage and code path where the producer's piece empties. The coverage comparison vs R is committed per group. For every group not settled by H1 / H5, exactly one of H2 / H3 / H4 is established with the proof the contract requires, or the group stays open with its RC named.
- **Scratch cleared (part of the outcome):** keep stage trace, coverage JSON, and (on H4) the full-PBF query result or, if too large to commit, its sha256 + exact argv (committed). Delete the `d35b565` worktree and window builds, stage-hook build, raw query dumps, temp dirs. Proof: the phase's `scratch_receipt` (see "Scratch hygiene").
- **Surfaces:** `p8_source_removed/` (stage trace, coverage JSON; full-PBF query output if H4), `output/scratch-64/` (windows; gitignored).
- **Approach:** open (the hook point in the EO stitch is not settled; the outcome is the yardstick). **Depends on:** Phase 1. **Refine:** hook point.

### Phase 3 — Act and update the residual

- **Outcome:** R-G5-1-b, R-G5-4-a-2 and R-G5-4-b-1 are each discharged with the per-group proofs, or replaced by exact per-group children with proven RCs. If H2 or H5: the fix lands with tests, and a successor oracle is accepted by Design (confined diff vs `0c22b266…`, R-DVD no-worse, Perth checked). The classifier tool and its 23-group output are committed. `residuals.tsv`, `causes_residual.md` note, ledger row. No waiver or "carried" end state.
- **Scratch cleared (part of the outcome):** keep the fix + tests, `successor_oracle_<sha>.json`, the promoted disc at the disc-in-force path named in the oracle record (outside scratch), the classifier tool, `residuals.tsv`, `causes_residual.md`, ledger row. Delete the whole `output/scratch-64/`: candidate encodes that were not promoted, AU / Perth build trees, K1 dump dirs, decoded discs, any `keep/`; a re-built spool unless it is promoted as spool of record (then it moves to that path). Proof: the phase's `scratch_receipt` (see "Scratch hygiene").
- **Surfaces:** `phase3_synthesis/residuals.tsv`; `causes_residual.md`; on H2 `parser/kiwiw/_cenc.c` + tests + oracle record under `triage/…/successor_oracle_<sha>.json` + `docs/OVERVIEW.md` oracle line; on H5 `parser/osm_to_parcel_geometry.py` + tests.
- **Approach:** known (per established hypothesis). **Depends on:** Phase 2. **Refine:** only if H2/H5.

## Provenance

- Tip: GitHub `origin/master` **`61d2fe8`** (plan 63 close-out, 2026-10-09 14:30 AEST); first grounded at `8498eec`.
- Revision sources (2026-10-09): `residuals.tsv` R-G5-4-a-2 / R-G5-4-b-1; `docs/plans/62-r01-still-outside-r16.md`; `p9_r01_residual/{transitions.json (d51baafb…), redecide.tsv.gz (9c47f1ef…), u4f_probe.json}`; `docs/plans/63-producer-ambiguous-tie-rc.md`; `p7_producer_tie/sidecar/sidecar_33006aa.patch`; `docs/plans/51-l0-type288-road-trim.md`. Design Ground on the box: producer distances, column counts and distinct-producer counts from `transitions.json`.
- Sources at tip: `residuals.tsv` R-G5-1-b; `docs/plans/46-bg-producer-scan-rebuild.md` (Phase 3 table, Residual Risks); `p6_producer/verdicts.tsv.gz` (`ca4a555a…`), `identity_remainder.tsv.gz`, `phase23.py` L141–157; `docs/provenance.md` L211–216, L854–855; `parser/kiwiw/spool.py` column list; plan 44 `p5_owner_exclusive/phase2_decisions_full.tsv.gz` (`3d221b6f…`; 469 `disagree_source_removed`, a 37 / b 432).
- Design Ground computation on the box: the vertex/edge breakdown of the 50 rows (Problem item 2).
- Siblings: **63** (closed; its sidecar is used here), **62** (closed; routed R-G5-4-a-2 / R-G5-4-b-1 here), **68** (re-bases on any oracle this plan moves).
- Rejected: discharging on "not failing on `4ed9cd80`" alone; H4 with only one proof; waivers; carried as an end state.
- Box draft only. No commit from Design.
