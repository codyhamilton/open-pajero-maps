---
design_id:
---

# K1 name_anchor failure: O03 at L0 (0,541) leaf 928

## Intent

Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Root-cause and fix (or prove a non-deviation for) the single K1 name_anchor failure that makes K1 exit 1. First identify the failing case precisely from code/tests/records on master. Execute pushes straight to master, with no feature branch and no PR. Do not reseat 170, 3-16, 3-17; do not draw plan 04 phases 4-6 or plan 06; do not claim plan 04 Phase 3 closed; no 3-90 re-run. Never relabel.

## Problem

### The failing case (identified on tip `0dc5cac`; re-checked on rebase to `3fb5a35`)

| Field | Value | Where proven |
| --- | --- | --- |
| K1 kind / level | `name_anchor`, L0 (every other level 0 failing) | Live K1 on `4ed9cd80…`: `output/scratch-14/k1_full.json` (Phase 1) and `p3/k1_p3.json` (post-3-03), both `totals.name_anchor = {checked 2,317,056, failing 1}`; the plan 14 record (`docs/plans/14-completeness-root-cause.md`) and its F1 resolution ("name_anchor 1 is pre-existing… K1 still exits 1") |
| G item | cell `[0, 541]`, `leaf_path [928]`, vertex raw `[0, 370]`, lat `-38.727284749`, lon `90.0` | Same reports, `levels.0.failures` sample (read-only host read 2026-10-06), identical to plan 04 `IMPLEMENTATION.md` L130 and plan 03 brief 3C-04 L133 |
| Reason | `no spool record within half a raw unit`. `quantisation_roundtrip._check_points` checks G→spool only: the nearest spool name to the rounded G anchor must be ≤ `TOL` 0.5 raw. The `_halo_name_rescue` does not apply (not a sub-cell halo) | `parser/tools/quantisation_roundtrip.py:750–772, 798–826, 934` |
| Spool source | `(L0, home (0,541), name record 0, type 288, string_type 6)`, spool lat `-38.727284749`, lon `77.51903576666666` (Île Saint-Paul). Chebyshev separation from G anchor is 1,635,904.943991 raw | plan 04 `triage/cause_table.md` O03; `rules_other.json` O03 note; `review_3-08.md` item 7 |
| Mechanism | The pre-plan-18 extractor `assign_to_parcel` clamped the negative `_lon_delta` (raw ix −399) into edge cell ix 0. `_make_name_record` stored the unmodified lon. The encoder's documented `_cenc.c:to_xy` clamp then faithfully placed it at lon 90.0, raw (0,370), leaf 928. A 3-08 window counterfactual removing only that name gives name_anchor 1→0 (1/1 G frame) | `cause_table.md` O03; rule O03 (spool) |
| Code fix already on master | Plan 18 (`16e2931`): `assign_to_parcel` (extractor and `mesh` twin) returns `None` for out-of-span lon. Tests `test_name_anchor_o03_extractor.py` (synthetic PBF), `test_parcel_geometry.py:119–122`, `test_descriptor.py:47` | `docs/plans/18-name-anchor-l0-extractor.md` |
| Why it still fails | The spool in force (`output/extract_timing/spool`) was restored in plan 14 from extractor tree `34a04cc` (2026-09-21), an **ancestor of** plan 18's `16e2931`. So the spool still holds the clamped name. Plan 18 explicitly excluded re-encode ("on-disc O03 pin remains until a future extract+encode"). The disc in force is still `4ed9cd80…` | plan 14 record (Deviations: spool incident); `git merge-base --is-ancestor 34a04cc 16e2931` → true |

### What is not proven

Every record above proves the item against the **spool** contract (G vs spool, K1). **No record on master compares this name with the original DVD (R).** 3-06 D7 decoded G and searched spool neighbours. 3-08's "original window matches 1/1 G frame" is a pre-change *G* rebuild control, not R. Plan 18 justified the fix by the extractor contract and a synthetic fixture.

Under the standing rule, the deviation that matters is G vs R:

- **If R carries no such name** (or a different one) at that leaf: G emits a name the DVD lacks. That is a real deviation, root cause O03, and it is fixed only when the generated disc no longer carries it.
- **If R carries the same name record at raw (0,370)**: the original toolchain clamped too, so G matches the DVD. Plan 18's extractor change would then *introduce* a DVD deviation on the next extract.

### Other facts that shape the fix

- Plan 14 rejected a tip-extractor spool rebuild because **138/775** witness cells differed for reasons unrelated to O03. A full re-extract would therefore conflate unrelated content changes into any re-oracle.
- Plan 03 brief 3-10 had proposed an **assembly drop guard** for stale spools (drop a name whose anchor lies outside its cell rectangle, counted per level, no silent clamp). It was held. Plan 18 lists it as an optional follow-up.
- K1 on tip has no spool→G name-completeness direction, so a G without this name raises no new name failure. Phase 2 re-measures this rather than assuming it.

The ticket is **not** already satisfied: K1 still exits 1 on the disc in force, and DVD parity for the item is unproven. Verified on `origin/master` `0dc5cac85deb3e7d9d919a66742f97aac674bc4f` and re-checked after rebasing onto `3fb5a35`, where plan 14 is closed out and lists name_anchor 1 as outside its scope.

## Solution shape

1. First prove the item against R.
2. Then either fix G so it no longer carries the item, or prove G matches R and fix the checker's spool-contract model.

Exactly one branch closes, chosen by Phase 1 evidence, not by preference. The fix never loosens a K1 tolerance and never relabels.

### Domain: item identity and DVD parity witness

- **Owns:** the committed byte-level identity of the single failing name_anchor item across G, spool and R, and the A/B verdict.
- **Contract:**
  1. **G witness:** disc `4ed9cd80…`, L0 cell (0,541), leaf 928. Record frame offset, length and sha256, plus the decoded name record (string bytes, string_type, class, raw x/y) that K1 flags.
  2. **Spool witness:** level-0 cell (0,541) name record 0. Record byte offset, length, hash, lat/lon, and the K1 nearest distance.
  3. **R witness:** disc `8c2d2027…` (plan-14 R pin). Decode the covering leaf or leaves of L0 cell (0,541) and its 8 neighbours. Record every name record whose string bytes equal G's, or state there is none, with raw positions.
  4. **Verdict:**
     - **A:** R lacks the same name at G's raw position (±0.5 raw). G≠R; root cause O03.
     - **B:** R carries the byte-equal name record at G's raw position. G==R for this item.
  5. **Whole-spool prediction:** count every spool name record, at any level, that the plan-18 contract would reject (out-of-span lon or lat). Expected exactly 1 (this item); any extra is listed with identity.
  6. All reads are single-cell `pread`s or a streamed name scan. Anything touching the full disc or spool goes through `run_heavy_python.py` (which takes `output/.heavy.lock`), with no whole-file loads.
- **Non-goals:** no fix in this domain; no other kind; no completeness work (plan 14 / draft 28).

### Domain: fix or proven non-deviation

- **Owns:** making K1 exit 0 on the disc in force for this item without relabel, recorded against R.
- **Contract, verdict A (G≠R):**
  1. The generated disc stops carrying the O03 name. The plan-18 contract (points outside the disc's coverage are not encoded) is applied to the in-force inputs by one Phase-2-chosen route (see Phase 2 approach). Every dropped item is counted per level and must equal Phase 1's prediction; any extra drop is root-caused or the phase fails.
  2. A new AU disc is built under `run_heavy_python.py` (which takes `output/.heavy.lock`), `-j4`, **at a new path** (e.g. `output/scratch-29/G_new/ALLDATA.KWI`). Both protected discs, `output/scratch-14/G_new/ALLDATA.KWI` (`4ed9cd80…`) and `output/scratch-3-11/G_new` (`013586b5…`), stay byte-untouched. The new disc is recorded as the **successor re-oracle**:
     - new sha256;
     - byte diff vs `4ed9cd80…` confined to the frames covering L0 (0,541), with the exact changed-leaf list;
     - `4ed9cd80…` retained as the historical oracle.
  3. Live K1 at `-j6` on the new disc shows:
     - name_anchor failing **0**;
     - name_anchor checked drops by exactly the dropped count;
     - completeness checked 1,800,514, failing 0;
     - every other kind's checked/failing identical to the plan-14 F1 live run (`runs/rem01_k1_live.json`);
     - **K1 exit 0**.
  4. R parity: G's leaf-928 name set equals R's at that leaf, or every residual difference is named.
  5. Perth fixture sha `da13a775…` and goldens are unchanged, or any change is explained.
  6. A synthetic positive control proves K1 still fails when an in-span name is missing or misplaced in G, i.e. the checker is not loosened.
- **Contract, verdict B (G==R):**
  1. No G change.
  2. A committed byte-equality proof of the R and G name record.
  3. K1 models the encoder's documented `to_xy` clamp narrowly: a spool name whose coordinate is outside the lattice span is compared at its clamped position, counted as an explained category like `name_anchor_halo`, and no tolerance changes. Live K1 then shows name_anchor 0 with build sha `4ed9cd80…` unchanged.
  4. A positive control: an in-span misplaced name still fails.
  5. A recorded **conflict finding** for Design: plan 18's extractor contract would drop an R-present name on the next extract. This plan does not revert plan 18.
- **Non-goals (both branches):**
  - no full tip re-extract as the default route;
  - no unfreezing of plan 03 content phases;
  - no plan 04 phases 4–6 or plan 06;
  - no 3-90 re-run (if the oracle moves, the 3-90 brief and plan-27 ledger get a successor-pin note only);
  - no Phase 3 close;
  - 170 / 3-16 / 3-17 not reseated.

## Decisions

1. Plan number **29** (28 is the plan-14 per-rule classify recovery drafted alongside). Land on master directly. No feature branch. No pull request.
2. Two phases. Phase 1 approach is known. Phase 2's outcome is fixed per verdict and its approach is **open**: for A, the regeneration route is chosen under a divergent-candidate method against the Phase 2 outcome. Refine skipped for Phase 1. Phase 2 runs a short candidate comparison only, no separate refine document. One worker may carry both.
3. R is the arbiter. Neither the spool contract nor plan 18 alone decides whether this is a deviation.
4. The failing case is pinned as `name_anchor` L0 cell (0,541), leaf 928, G raw (0,370), lat −38.727284749 / lon 90.0, from spool name `(L0, home (0,541), record 0, type 288, string_type 6)` at lon 77.51903576666666. Phase 1 must re-observe exactly this. A different item means the ticket premise has drifted, and Phase 1 records that instead.
5. A re-oracle (verdict A) is the honest fix route, because a G≠R deviation with an already-landed code fix is not closed while the disc in force still carries it. It is recorded in `docs/provenance.md` and the OVERVIEW disc-in-force line. The previous oracle is retained as history.
6. Heavy steps (full-AU encode, K1, whole-spool scans) run only through `run_heavy_python.py`, which takes `output/.heavy.lock`, at the existing caps (encode `-j4`, K1 `-j6`). This plan does not override a CHM hold decision.

## Assumption ledger

### Assumption 1

- **Question:** Is the failing item still exactly the O03 name on the disc in force?
- **Answer chosen:** Yes. The live K1 samples on `4ed9cd80…` (both pre- and post-3-03) show exactly cell [0,541], leaf [928], raw [0,370], lon 90.0, and the only failing name_anchor at any level.
- **Rationale:** Read-only host read of the saved K1 JSONs; plan-14 records.
- **If wrong:** Phase 1 records the drifted item and the root cause starts over from its witnesses. Phase 2 is unchanged in shape.

### Assumption 2

- **Question:** For verdict A, which regeneration route?
- **Answer chosen:** Open, with candidates:
  - **(a)** An assembly-time drop guard implementing the plan-18 coverage contract on the in-force spool (counted per level, no silent clamp). The spool stays byte-unchanged, so plan-14 spool witness pins stay valid.
  - **(b)** Cell-scoped regeneration of the affected spool cell(s) with the tip extractor, accepted only if the cell diff is exactly the O03 record removal.
  - **(c)** Full tip re-extract plus encode with full changed-cell accounting. **Rejected as default**, because 138/775 witness cells differ for unrelated reasons.
- **Rationale:** The outcome is fixed. (a) and (b) both confine the change to the item, and they differ on provenance: a build rule vs a hybrid spool.
- **If wrong:** Cody orders (c). That becomes a separate, wider re-oracle design, because it changes unrelated content.

### Assumption 3

- **Question:** Does fixing a spool-caused item contradict plan 04 Phase 3's taxonomy (spool items carried to the successor list)?
- **Answer chosen:** No:
  - Phase 3's carry rule governs what may remain failing at Phase 3 close. It does not forbid fixing an item whose fix contract already landed (plan 18).
  - This plan fixes one item and does not draft the successor design.
  - Plan 04 Phase 3 stays open.
- **Rationale:** The user asks to fix or prove non-deviation, and plan 18 already landed the contract.
- **If wrong:** Cody keeps O03 carried. Phase 2 lands verdict-A evidence only (R witness plus a counterfactual disc in scratch, not a re-oracle), and K1 stays exit 1 on the disc in force. Recorded as such.

### Assumption 4

- **Question:** Does moving the oracle (verdict A) require re-running 3-90 or plan-14 evidence?
- **Answer chosen:** No:
  - Phase 2 proves no collateral via K1 per-kind equality and the confined byte diff.
  - The 3-90 brief Contract and the plan-27 ledger get a successor-pin note, with no 3-90 run.
  - Plan-14 evidence stays valid as measured on `4ed9cd80…`.
- **Rationale:** No 3-90 re-run is a hard constraint, and the confined diff makes collateral checkable.
- **If wrong:** Cody requires 3-90 on the new oracle. That stays under plan 04, not here.

### Assumption 5

- **Question:** Could K1 need a matching change under verdict A?
- **Answer chosen:** Only if Phase 2 measures a new failure. Tip K1 checks names G→spool only, so a G without the name should not fail. Any K1 change must be counted, rule-documented and positive-controlled, never a tolerance change.
- **Rationale:** Never loosen. Measure instead of assuming.
- **If wrong:** The K1 change is added to Phase 2's surfaces with its control.

## Open questions

1. The name string bytes. They are not committed on master (cause_table records type and string_type only). **Phase 1 records them.**
2. Route (a) vs (b) under verdict A. **Phase 2 decides** against the fixed outcome.
3. Whether the assembly drop guard should also stay as permanent defence-in-depth after a future full re-extract. **Out of scope.** Plan 18 follow-up territory.

## Phases

### Phase 1: The single name_anchor failure is byte-identified against G, spool and R

- **Outcome:**
  1. A committed record pins the item as K1 `name_anchor`, L0 cell (0,541), leaf 928, G raw (0,370), lat −38.727284749 / lon 90.0, reason "no spool record within half a raw unit", on disc `4ed9cd80…`.
  2. It records the **G witness**: frame offset, length, sha256 and decoded name record (string bytes, string_type, class).
  3. It records the **spool witness**: L0 (0,541) name record 0 bytes and hash, lon 77.51903576666666, K1 nearest distance.
  4. It records the **R witness** on `8c2d2027…`: covering leaf frames of L0 (0,541) and its 8 neighbours, hashed, and every byte-equal name record with its raw position, or "none".
  5. It states verdict **A** (G≠R) or **B** (G==R), with the evidence.
  6. It shows tip `assign_to_parcel(-38.727284749, 77.51903576666666)` → `None` (existing tests cited) and that the in-force spool was produced by pre-plan-18 extractor tree `34a04cc`.
  7. A whole-spool count of name records the plan-18 contract would reject gives exactly 1, or lists every extra with its identity.
  8. Not done here: no G, spool, encoder, checker or rule change; no K1 re-run needed (the saved live K1 is cited; a light single-leaf decode is allowed). Heavy reads ran only through `run_heavy_python.py` (which takes `output/.heavy.lock`).
- **Surfaces:**
  - new `docs/plans/29-k1-name-anchor-failure/` record (witness note and small witness TSV/JSON);
  - read-only: `parser/kiwiw/` decoders, `parser/osm_to_parcel_geometry.py`, `parser/tools/quantisation_roundtrip.py`, `output/extract_timing/spool`, `output/scratch-14/G_new/ALLDATA.KWI`, the R disc.
- **Approach:** known.
- **Depends on:** master at or after `3fb5a35`; the disc `4ed9cd80…`, spool and R disc present on the host (as used by plan 14).
- **Refine:** skipped.

### Phase 2: K1 exits 0 on the disc in force, with no relabel and parity recorded against R

- **Outcome (exactly one):**
  - **A:**
    1. The O03 name is absent from the generated disc via the chosen route, with drops per level equal to Phase 1's prediction.
    2. A new AU disc is built under `run_heavy_python.py` (which takes `output/.heavy.lock`) at a new path, with both protected G_new discs untouched, and recorded as the successor re-oracle: full sha256, byte diff vs `4ed9cd80…` confined to the frames covering L0 (0,541), exact changed-leaf list.
    3. Live K1 `-j6` shows name_anchor failing 0, name_anchor checked −(drop count), completeness 1,800,514 / 0, every other kind identical to `rem01_k1_live`, **exit 0**.
    4. G's leaf-928 names equal R's, or each residual difference is named.
    5. Perth `da13a775…` and goldens unchanged, or explained.
    6. A positive control (missing or misplaced in-span name) still fails K1.
    7. `docs/provenance.md`, OVERVIEW's disc-in-force line, and the 3-90 brief / plan-27 successor-pin note are updated.
  - **B:**
    1. A committed R/G byte-equality proof.
    2. A narrow K1 clamp model, counted as an explained category with no tolerance change, gives name_anchor 0 with sha `4ed9cd80…` unchanged and **exit 0**.
    3. A positive control still fails.
    4. A recorded conflict finding against plan 18 for Design.
  - **Both branches:**
    - `rules_other.json` O03 note updated to state the item's disposition;
    - tests under `parser/tests/` pass;
    - no tolerance loosened;
    - no 3-90 re-run, no plan 04 phases 4–6 or plan 06, no Phase 3 close, 170 / 3-16 / 3-17 not reseated.
- **Surfaces:**
  - **A, route (a):** `parser/build_alldata.py` (and the encoder input path only as needed) for the counted guard.
  - **A, route (b):** a tracked cell-scoped spool regeneration step.
  - **B:** `parser/tools/quantisation_roundtrip.py` plus the C K1 twin (`parser/kiwiw/_k1*.c`) for parity.
  - **Always:** `parser/tests/`, `docs/plans/04-c-core-orchestration/triage/rules_other.json` (O03 note), `docs/provenance.md`, `docs/OVERVIEW.md`, the plan-29 record.
- **Approach:** open (route choice under A; scored only against this outcome).
- **Depends on:** Phase 1 verdict.
- **Refine:** none beyond the candidate comparison recorded in the plan-29 record.

## Provenance

- Ground tip read: `origin/master` `0dc5cac85deb3e7d9d919a66742f97aac674bc4f` ("K1 completeness representability: full EO topology (plan 14 remediation-01, review F1)"). **Rebased by Execute onto `3fb5a35` (2026-10-06):** plan 14 is collapsed to its record, and its triage moved to `docs/plans/04-c-core-orchestration/triage/`. The failing item and K1 totals are unchanged (`runs/rem01_k1_live.json`). The rebase adds the constraint that any successor disc is written to a new path with both protected G_new discs untouched.
- Evidence cited (committed):
  - plan 18 closed record;
  - plan 04 `triage/{cause_table.md, rules_other.json, review_3-08.md, rebaseline_3-17_9064.md}` and `IMPLEMENTATION.md` (L130, L145, L225, L429, L520);
  - plan 03 briefs `3-10-name-cell-clamp.md`, `3C-04-roundtrip-redesign.md` L133;
  - the plan 14 record `docs/plans/14-completeness-root-cause.md` (spool restore from `34a04cc`, 138/775 rejection, name_anchor 1 out of scope, review);
  - `parser/tools/quantisation_roundtrip.py` (`_check_points`, `_halo_name_rescue`, `TOL`);
  - `parser/kiwiw/_cenc.c:145` `to_xy`;
  - tests `test_name_anchor_o03_extractor.py`, `test_parcel_geometry.py`, `test_descriptor.py`.
- Read-only host Ground on `codyh-ubuntu`: `levels.0.failures` name_anchor sample and `totals.name_anchor` from `output/scratch-14/k1_full.json` and `p3/k1_p3.json`; `runs/k1_p3.json` (exit 1, memory_peak 4,316,889,088 B). No K1, encode, or disc/spool read was run for this design.
- No record on master compares the O03 name with R; this design makes that the Phase 1 gate.
- Rejected for this design:
  - treating the spool-contract proof as DVD parity;
  - full tip re-extract as the default;
  - loosening `TOL` or adding a catch-all explained category;
  - reverting plan 18 here;
  - a 3-90 re-run;
  - plan 04 phases 4–6 or plan 06;
  - Phase 3 close;
  - reseating 170 / 3-16 / 3-17.
- Draft format followed: `/workspace/maps-design-drafts/27-independent-fix-review-truncated-pins/DESIGN.md`.
- Design method: the workflow design skill (headless assumption ledger).
- The adversarial pass ran in-context, not in a clean context; that is disclosed. It applied two findings: the missing R comparison (hence the A/B verdict gate) and the 138/775 conflation risk (hence full re-extract rejected as default).
- Workflow-service posts and `artifact_feedback` were skipped under the user instruction. Box draft only: no commit or push.
- Plan 04 Phase 3 stays open. This plan does not draw phases 4–6 or plan 06. Plans 170 / 3-16 / 3-17 are not reseated.
