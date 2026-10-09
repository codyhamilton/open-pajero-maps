---
design_id:
---

# Producer-ambiguous duplicate records: tie proof, E2 emission-order root cause, per-row decision (R-G5-1-a, R-G5-2-a, plan-46 scope delta)

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Cody's hard bar as restated for this work (2026-10-08): Maps is complete only when end-to-end generation matches the original DVD in every verifiable aspect. Every deviation needs a proven root cause. No waivers, and carried is not closed. Never pick an arbitrary rule and call it proven.

Design brief (Execute hand-off after plan 46 closed at `8498eec`): produce a tie rule or RC path for the producer_ambiguous children R-G5-1-a (4,594 rows / 96 groups) and R-G5-2-a (18 rows / 2 groups), and for the two open scope-delta leaves (1481,1288) and (1754,1158). (a) Split the groups: byte-identical candidates are proven-producer-tied (deterministic lowest key, both IDs recorded); non-identical candidates need a real RC. (b) Derive the builder's selection rule from evidence, test candidate rules against a proven set, accept a rule only at 100% with a holdout; otherwise each group stays open with its own RC. (c) Apply to R-G5-1-a, R-G5-2-a, (1481,1288) and (1754,1158), decide per row, discharge or name the RC for each.

Master direct. Heavy work under flock + `run_heavy_python.py --memory-max 12G`, encode `-j4`, K1 ≤ `-j6`. No nearest-ring choice. No waivers. No oracle change from this plan (live AU `0c22b266…`, Perth `5b86d33e…`). No plan 04 P4–6, no 3-90, no reseat 170 / 3-16 / 3-17. No F6 / kind-order / roads-preference / L8-expansion work (Cody open). Assigned Execute instance: OpenCode DeepSeek Flash (Design does not start workers).

**Scratch-rule note (Design, 2026-10-09):** Cody's standing rule added: every phase outcome now includes a scratch receipt with named keep / delete lists (see "Scratch hygiene" and each phase). No other change to this draft.

## Problem

**Ground (GitHub `origin/master` `8498eec`, plan 46 close-out, fetched on the box 2026-10-08 ~10:45 AEST; read-only):**

1. **The 98 groups.** `p6_producer/verdicts.tsv.gz` (sha256 `ca4a555a…`, content `775ac6c0…`): `producer_ambiguous` = **4,612 rows / 98 (leaf, shape) groups / 47 leaves / 46 cells** — R-G5-1-a background_boundary 4,594 rows / 96 groups / 46 leaves (42 depth-1, 4 depth-2); R-G5-2-a background 18 rows / 2 groups / 1 leaf ((0,1176,1591,(1784)) shapes 1 and 3, 9 rows each). By type: 288 → 3,764 rows, 291 → 516, 578 → 332. This is the same 98-group "2+ candidate rings" class as `causes_residual.md` L125, whose recorded next predicate is *"Ordered E2 class-2 record-sequence provenance, including divided-leaf keep-order; do not choose a nearest ring."*
2. **No candidate IDs are committed for the 98.** Their verdict rows carry `producer_hx/hy/ri = -1` and `extra = {"depth","producer_raw"}` only. `p6_producer/tie_probe.py` hard-codes the three scope-delta leaves. The per-group candidate lists must be regenerated before anything is decided.
3. **Every ambiguous leaf holds its ambiguous shapes as equal-content pairs** (Design Ground read of the verdict rows; compares failing-row vertex content only, not full record bytes): 45 leaves have exactly 2 ambiguous shapes with one distinct content; 2 leaves have 4 shapes forming 2 pairs — (0,1031,1525,(1703)) {2,6},{3,7} and (0,1032,1526,(1736)) {8,11},{9,12}. Shape-index gap inside a pair: 1 (18 leaves), 2 (17), 3 (3), 4 (1), and 8 / 16 / 24 / 127 / 1,420 / 1,942 (1 each). So the class is "a leaf holds two copies of one record and two same-type candidates byte-hit it", not "one record, two possible owners".
4. **Scope delta (plan 46, `ties.json`, 6 groups / 512 S02-scope rows, outside S).** These 6 groups are **the same leaves and shapes as 6 of the 98 remainder groups** (Design Ground join on `verdicts.tsv.gz`): (1481,1288) shapes 0/2 at 75 + 75 rows, (1753,1158) shapes 1/2 at 120 + 120, (1754,1158) shapes 1/3 at 63 + 63. That is 516 remainder rows, which are exactly all of R-G5-1-a's type-291 rows. The S02-scope row counts differ slightly (119 and 62 per shape, because scope counts only L0/291/sentinel candidate rows). So the 240 remainder rows at (1753,1158) are already proven-producer-tied by plan 46 but still carry `producer_ambiguous` in `verdicts.tsv.gz`.

   | Leaf (shapes) | Candidates (hx,hy,ri,type) | Whole clip blob | Pieces → leaf shapes | Plan 46 verdict |
   | --- | --- | --- | --- | --- |
   | (0,1753,1158,(217)) 1, 2 | (1755,1157,1,291), (1755,1157,2,291) | identical `e5b7534e…`, 1 piece | P → {1,2} for both | proven-producer-tied; lowest key (1755,1157,1) |
   | (0,1481,1288,(265)) 0, 2 | (1485,1280,0,291), (1486,1280,0,291) | differ | A: P → {0,2}, other → {1}; B: P → {0,2}, other → {3} | open, RC owed |
   | (0,1754,1158,(218)) 1, 3 | (1755,1157,1,291), (1755,1157,2,291) | differ | A: P → {1,3}, other → {2}; B: P → {1,3}, other → {4} | open, RC owed |

   In both open leaves the shape order is exactly A-block then B-block: (1481,1288) = [A.P, A.other, B.P, B.other] = shapes 0,1,2,3; (1754,1158) = shapes 1,2,3,4. That fits "each candidate emitted its own copy of P as a contiguous block, candidates in key order". It is **not proven**; it is the leading hypothesis this plan must prove or reject.
5. **The emitter is observable.** The ambiguous records sit on `013586b5`, the 3C-04 G disc built by our own encoder at `33006aa` (plan 36 / plan 45 rebuilt `33006aa` → `013586b5` byte-equal; `docs/provenance.md` L854). So the "builder's selection rule" here is our E2 record emission at `33006aa`, which can be instrumented output-neutrally — the provenance that `causes_residual.md` L125 names and that plan 45 ("source-tag sidecar not landed") and plan 48 ("input-ring IDs into the split are not instrumented") did not have.
6. **Plan 46 limits that bind here:** "no nearest-ring choice"; the lowest-key tie-break was ruled only for whole-blob identity; `4ed9cd80` = `33006aa` + `hop_3_14/eo_only.patch` (`docs/provenance.md` L855), so the decide limb's new-disc side is the EO-stitch change alone.

**Why the plan-46 tie rule is not yet enough even for byte-identical candidates.** Two candidates can share an identical `33006aa` clip blob while their source rings differ (240 vs 375 vertices at (1753,1158)). The decide limb re-clips the *producer ring* with the `d35b565` clipper; two different rings can clip differently there. A lowest-key tie-break is parity-neutral only if every tied candidate yields the same decide verdict.

## Solution shape

### Domain: tie census (all ambiguous groups)

- **Owns:** a generalised tie probe over all 98 remainder groups / 47 leaves (which include the 6 scope-delta groups), under `triage/historical_bg/p7_producer_tie/` (new folder; plan-46 `p6_producer/` files are read-only inputs).
- **Contract:**
  1. Candidate set per group = plan 46's (RC2 piecewise, RC3 FarHomes, RC4 `leaf_clip_geometry`, RC5 same type, RC6 raw-unit stats), R=8 ∪ far bbox-meet, clipper `33006aa` `_cenc.c` — unchanged from `bg_producer_scan.py` / `tie_probe.py`.
  2. Per group: every same-type hit with whole clip blob sha, piece shas, piece → leaf-shape map, all-pieces-on-disc flag, source ring sha; full record-byte identity of each duplicate pair on `013586b5`.
  3. Per candidate: the unchanged phase-23 decide limb (`d35b565` clip into the leaf; byte or owner-exclusive vertex on a `4ed9cd80` same-type record; K1 `k1head_314`/`k1old_314` cite) and its verdict.
  4. Class per group, exactly one of:
     - **T1 proven-producer-tied:** ≥2 same-type hits, whole clip blobs byte-identical **and** identical decide verdict for every hit. Identity column = lowest (level,hx,hy,ri); **all** candidate IDs recorded. Parity-neutral by construction.
     - **T2 open:** ≥2 hits and the blobs differ, or the blobs are identical but the decide verdicts differ → Phase 2.
     - **T0 reclassified:** fewer than 2 same-type hits under the plan-46 scan → named with the step that changed (row-by-row; never silently absorbed).
  5. Deterministic: gz mtime=0, sorted keys; run twice, byte-identical.
- **Non-goals:** changing `bg_producer_scan.py` defaults; changing plan 46's committed S, identities or verdicts files.

### Domain: E2 emission provenance and rule derivation

- **Owns:** an output-neutral source-tag sidecar for the `33006aa` encoder (patch + driver committed under `p7_producer_tie/`, built in a throwaway worktree at `33006aa`, as plan 36 did for its endpoint rebuilds), single-cell window builds, a proven-producer set, and the rule evaluation.
- **Contract:**
  1. **Output-neutral gate:** with the sidecar on, every window cell's frames are byte-equal to the `013586b5` full-reference frames (plan 45's window-control method). Any byte difference stops the domain (stop_for_design).
  2. **Sidecar control gate:** for every record in the window cells that the plan-46 scan calls `unique-byte`, the sidecar's emitting source equals the scan's producer, 100%. Disagreements are named row-by-row and stop the domain.
  3. **Per-copy provenance:** for each T2 group (and each T1 group, as a check), the sidecar names the emitting source of every copy. That is a direct proof of the producer per copy; it does not depend on any rule.
  4. **Selection-rule derivation (brief item b):**
     - Proven set = records whose producer is fixed by the sidecar, or by a distinguishing second piece that exactly one candidate emits (the plan-46 `ties.json` pattern), drawn from the window cells plus a stratified sample of other cells with ≥2 same-type candidates.
     - Holdout = a disjoint cell set chosen by a fixed cell-hash before any rule is scored, at least as large as the derivation set and stratified by kind / type / depth.
     - Candidates to score, at least: candidate key order (level,hx,hy,ri); nearest home; spool record order in the home cell; disc / dump record order; block / blockset order; contiguous per-producer block emission with piece order preserved; first emitter of a duplicated record; divided-leaf keep-order.
     - A rule is **accepted** only at 100% on the derivation set **and** 100% on the holdout, **and** with the `33006aa` E2 code path that implements it cited (file and function). Rules that reach 100% without a code path are reported as empirical and are not used to discharge any row.
     - If no rule passes, no rule is adopted; each group keeps its per-copy sidecar proof (item 3) or stays open with its own named RC.
- **Non-goals:** changing master's encoder or any disc output; nearest-ring choice; tuning rules to fit.

### Domain: per-row decision and residual update

- **Owns:** `p7_producer_tie/verdicts_ambiguous.tsv.gz` (sha-pinned + json), `residuals.tsv` rows R-G5-1-a / R-G5-2-a (owner/status/evidence), a `causes_residual.md` note, and the scope-delta record.
- **Contract:**
  1. Each copy of each group gets its proven producer (sidecar, accepted rule, or T1 tie) and the unchanged decide-limb verdict: `build:eo_bg_stitch`, or a named residual (`no-owner-exclusive-vertex`, `source-removed` → plan 64's classifier, or a new class with its RC defined).
  2. Rows compared one by one. The counts reconcile to 4,612 rows / 98 groups. The 6 scope-delta groups are also reconciled to their 512 S02-scope rows (516 remainder rows).
  3. **Scope delta vs S:** plan 46's committed S (`s02_full_predicate_groups.tsv.gz`, 145,954 / 11,127,333) is not mutated. If resolved scope-delta groups would qualify, publish S′ = S ∪ those groups with the plan-46 identities (entries = 451,185 − |S′| + 3; res bnd groups = 219,201 − a(S′); S04 groups = 219,032 − a(S′)) and confirm them with one `gate_repro --s02-scope full` run carrying the resolution as an opt-in input. Note: (1481,1288) shapes 0 and 2 are all-sentinel, so admitting both gives a(S′) = 15,080. The historical remainder figures (137 / 8,739, exact in plan 46) are not re-derived from a resolved producer. They stay the plan-46 gate. A resolution is a decide-layer fact about which source emitted each copy; it does not retro-edit the historical `residual_crossing_verified` semantics.
  4. **Duplicate-emission parity fact:** count leaves holding byte-identical same-type duplicate records on R (the DVD), on `013586b5`, and on live `0c22b266`. If G emits duplicates where R never does, open a new named residual row (owner Design) with the evidence. This plan does not fix it.
  5. R-G5-1-a / R-G5-2-a end as **discharged** (every row has a proven cause) or are replaced by **exact children** each with a proven RC. Neither "producer_ambiguous" nor "carried" is an end state.
- **Non-goals:** R01's 2,972 `producer_ambiguous` rows from plan 44 (they belong to plan 62's census; plan 62 may consume an accepted rule after this plan lands); R-G5-1-b (plan 64).

### Memory guardrails (all phases)

- Every heavy step is serial under `flock output/.heavy.lock` and `run_heavy_python.py --memory-max 12G` (cgroup MemoryMax 12G, MemorySwapMax=0). Encode / window builds at `-j4`; K1 at `-j6` or lower.
- Streaming per leaf / per shard. No whole-set in-memory grouping. Ring/cell caches are bounded (plan 46: LRU 4096) and spool caches are cleared between batches (`leaf_io.clear_spool_caches`).
- Any new scanning tool carries the plan-46 RssAnon watchdog (`bg_producer_scan.py --max-rss-mib`, cap 3072 MiB per shard) or an equivalent one.
- A watchdog trip or cgroup OOM is a stop_for_design with the measured peak and leaf index. Never raise the cap silently.
- Each phase's peak (wrapper max RSS, cgroup `memory.peak`, max shard RssAnon) goes into the plan-56 ledger as `docs/plans/56-cross-phase-rss-profile/ledger/producer_tie_plan63.json` plus a SUMMARY row.

### Scratch hygiene (all phases; Cody standing rule, 2026-10-09)

- **Rule (Cody):** Execute cleans its scratch after every phase, keeping only what the ledger or the next phase needs. **A phase is not done until its scratch is cleared.** The receipt below is part of every phase outcome.
- **This plan's scratch:** `output/scratch-63/`, any git worktree this plan adds, any temp dir its runs create (named in the run log), and the wrapper's cgroup scopes. Nothing else.
- **Never deleted by this plan:** `output/.heavy.lock` (shared flock file); other plans' `output/scratch-*` (some are pinned evidence, e.g. `oracle_chain/pin_contract.py` pins `output/scratch-32/…`); the spool of record; the R (DVD) image; the disc in force and earlier oracle discs; `.venv-rp`.
- **What may be kept:** committed artefacts first. Ledger rows carry the peak fields copied from the wrapper log, so the log itself is not kept. Anything the next phase needs that cannot be committed goes under `output/scratch-63/keep/`, listed with path, bytes and sha256, and is deleted at the end of the phase that consumes it.
- **Receipt** (`scratch_receipt` in the plan note, one per phase):
  1. `du -sb output/scratch-63` before cleanup and after;
  2. after: `test ! -e output/scratch-63` (gone), or `ls -A output/scratch-63` shows only `keep`, with its contents listed;
  3. `git worktree list` shows no worktree from this plan (after `git worktree remove` + `git worktree prune`);
  4. every temp dir named in the phase's run logs is gone, and no wrapper scope from the phase is still running;
  5. kept list checked: every kept path exists, committed paths appear in `git ls-files`, `keep/` items match their recorded sha256.
- A missing or failing receipt means the phase is not done. The final phase ends with `output/scratch-63` gone.

## Decisions

1. Plan number **63**. Master direct. Three phases: tie census; emission provenance and rule; apply and decide.
2. Primary proof per copy = direct E2 emission provenance (sidecar) on our own `33006aa` encoder. Rule derivation is still run, as the brief asks, to explain and generalise. A rule never overrides sidecar evidence.
3. Lowest-key tie-break only for T1, as defined above. All candidate IDs are recorded. It is never applied to T2.
4. The holdout is fixed by cell-hash before scoring. The acceptance bar is 100% on both sets plus a cited code path.
5. Plan 46's committed artefacts (S, identities, verdicts, `ties.json`) are inputs, not edited. New evidence lives under `p7_producer_tie/`.
6. Tip ground `8498eec`. Live oracle `0c22b266…` is used only for the duplicate-emission census; decide-limb discs stay `013586b5` / `4ed9cd80` as in plan 46.

## Assumption ledger

### Assumption 1

- **Question:** Is the lowest-key tie-break parity-neutral whenever the `33006aa` whole clip blobs are byte-identical?
- **Answer chosen:** Only if the `d35b565` decide verdict is also identical for every tied candidate (T1). Otherwise the group is T2.
- **Rationale:** The decide limb re-clips the producer ring with `d35b565`; tied candidates have different rings (e.g. 240 vs 375 vertices at (1753,1158)).
- **If wrong:** none. The added check can only move groups from T1 to T2.

### Assumption 2

- **Question:** Can an output-neutral source-tag sidecar be added to the `33006aa` encoder for window builds?
- **Answer chosen:** Yes. Single-cell windows at `33006aa` were already byte-equal to full-reference frames in plan 45, and plan 48 landed an output-neutral `eo_census` sidecar on the later encoder.
- **Rationale:** `provenance.md` L854–855 (throwaway worktrees at `33006aa`); plan 45 `window_control.json` ALL_OK.
- **If wrong:** Phase 2 stops for Design. The fall-back proven set is only the distinguishing-second-piece groups, and the rule bar is unchanged.

### Assumption 3

- **Question:** Does the duplicate-pair structure mean both candidates emitted a copy?
- **Answer chosen:** Hypothesis only. Phase 2 proves or rejects it per copy.
- **Rationale:** 47/47 leaves pair up; `ties.json` block order in both open leaves.
- **If wrong:** groups whose copies share one emitter are named with the sidecar's evidence.

### Assumption 4

- **Question:** May resolving scope-delta groups rewrite plan 46's S baseline?
- **Answer chosen:** No. Publish S′ alongside S using the proven identities, plus one confirming gate run.
- **Rationale:** Plan 46's double-run baseline stays reproducible; Design ruling (b) is preserved.
- **If wrong:** Design re-baselines explicitly in a later ruling.

## Open questions

1. Which `33006aa` E2 function emits background class-2 records per leaf (`_e2.c` vs `_cenc.c` stitch path)? Refine locates it. It must be cited for any accepted rule.
2. The minimum stratified sample size for the off-window proven set. Refine fixes it from the Phase 1 counts of leaves with ≥2 same-type candidates.

## Phases

### Phase 1 — Tie census committed

- **Outcome:** `p7_producer_tie/ties_all.json` covers all 98 groups / 47 leaves (the 6 scope-delta groups included). Each group is T1, T2 or T0, with candidates, blob/piece evidence, record-byte duplicate identity and per-candidate decide verdicts. Counts reconcile to 4,612 rows / 98 groups (scope-delta subset 516 remainder / 512 S02-scope rows). Plan 46's (1753,1158) T1 result is reproduced or the difference is named. Double run byte-identical. Peak recorded in the 56 ledger.
- **Scratch cleared (part of the outcome):** keep `p7_producer_tie/ties_all.json`, the probe + unit test (committed); 56-ledger row. Phase 2 reads only the committed T2 list. Delete `output/scratch-63/` contents: probe shards, per-leaf decodes, double-run copies once compared, wrapper logs once copied into the ledger. Proof: the phase's `scratch_receipt` (see "Scratch hygiene").
- **Surfaces:** `triage/historical_bg/p7_producer_tie/` (generalised probe derived from `p6_producer/tie_probe.py`), `parser/tests/` (probe unit test), `parser/perf_inventory.json`.
- **Approach:** known. **Depends on:** none. **Refine:** skipped.

### Phase 2 — Emission provenance and selection rule

- **Outcome:** The sidecar `33006aa` window builds of every affected cell (46 cells, which include the 3 scope-delta cells) are byte-equal to the `013586b5` frames. The sidecar agrees 100% with the scan's unique-byte producers in those cells. Every copy in every T2 (and T1) group has a sidecar-named producer, or a named reason it has none. A rule table scores every candidate rule on derivation and holdout: exactly one rule is accepted under Decision 4, or "no rule accepted" is stated.
- **Scratch cleared (part of the outcome):** keep sidecar patch vs `33006aa`, window driver, `provenance.tsv.gz`, `rules.json`, `docs/provenance.md` entry (committed); 56-ledger row. Plan 64 rebuilds from the committed patch in its own scratch; 63 holds no scratch for 64. Delete the `33006aa` git worktree and its build dir, all 46 window builds, decoded `013586b5` frame extracts, sampler outputs, temp dirs. Proof: the phase's `scratch_receipt` (see "Scratch hygiene").
- **Surfaces:** `p7_producer_tie/` (sidecar patch vs `33006aa`, window driver, `provenance.tsv.gz`, `rules.json`); `output/scratch-63/` (worktree, windows; gitignored); `docs/provenance.md` entry.
- **Approach:** open (the sidecar hook point and the proven-set sampler are not settled; the outcome above is the yardstick). **Depends on:** Phase 1 (T2 list). **Refine:** sidecar hook + sampler.

### Phase 3 — Apply, decide per row, update residuals

- **Outcome:**
  - `p7_producer_tie/verdicts_ambiguous.tsv.gz`, sha-pinned and double-run identical, gives every one of the 4,612 rows a proven producer and a decide verdict.
  - R-G5-1-a and R-G5-2-a are discharged, or replaced by exact children with a proven RC.
  - (1481,1288) and (1754,1158) are resolved or carry a named RC, and S′ is published if it differs from S.
  - The duplicate-emission census (R / `013586b5` / `0c22b266`) is recorded, with a new residual row if it shows a deviation.
  - `causes_residual.md` has its note. No waiver or "carried" end state.
- **Scratch cleared (part of the outcome):** keep `verdicts_ambiguous.tsv.gz`, `residuals.tsv`, `causes_residual.md` note, ledger row (committed). Delete the whole `output/scratch-63/`: duplicate-emission census intermediates (R / `013586b5` / `0c22b266` decodes), second determinism run, any `keep/`. Proof: the phase's `scratch_receipt` (see "Scratch hygiene").
- **Surfaces:** `p7_producer_tie/`, `phase3_synthesis/residuals.tsv`, `triage/causes_residual.md`, plan-56 ledger, optional `docs/OVERVIEW.md` ownership line.
- **Approach:** known. **Depends on:** Phase 2. **Refine:** skipped.

## Provenance

- Tip: GitHub `origin/master` **`8498eec`** (`8498eec21ba4d057cf70f3ad432612c7df223c3b`, plan 46 close-out, 2026-10-08 10:36 AEST).
- Sources at tip: `docs/plans/46-bg-producer-scan-rebuild.md`; plan 46 IMPLEMENTATION at `e7eba63` (RC0–RC6, tie probe, scope delta); `p6_producer/verdicts.tsv.gz` (`ca4a555a…`), `identity_remainder.tsv.gz` (`96093444…`), `ties.json`, `tie_probe.py`, `phase23.py`, `s02_full_predicate_groups.{tsv.gz,json}` (`7ab5a029…` / TSV `ae2ce385…`); `causes_residual.md` L125 and the plan-46 note; `residuals.tsv` R-G5-1-a / R-G5-2-a; `docs/provenance.md` L854–855; plan 45 `p4_ceiling/window_control.json`; plan-56 `ledger/bg_producer_scan_plan46.json`.
- Design Ground computation on the box: pair / gap / type / depth counts from `verdicts.tsv.gz` (item 3 of Problem).
- Siblings: **62** (R01 incl. R-G5-4-c; may consume an accepted rule later), **64** (R-G5-1-b; shares the Phase 2 sidecar), **65** (R-G5-4-a/b owner wording).
- Rejected: nearest-ring choice; lowest-key on non-identical candidates; rules accepted without a holdout or code path; mutating plan 46's S; waivers; carried as an end state.
- Box draft only. No commit from Design.
