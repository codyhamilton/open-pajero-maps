# Brief: 3-12 — Attribute the residual `background` / `background_boundary` rows (no pins without a mechanism)

Consumer: the orchestrator, who authors fix units 3-13+ from the result (checker fix, build fix) and updates `triage/cause_table.md`; the Sonnet 5.5 reviewer; later 3-90 only after PARTITION can honestly pass.
Owned paths: `docs/plans/04-c-core-orchestration/triage/rules_bg.json` (append/replace rules), new `triage/causes_residual.md`, `output/scratch-3-12/` (git-ignored). No code edits, no fixes, no commits (the orchestrator commits after review). Do not touch `output/scratch-2-07/`, `output/scratch-3-06/`, the old oracle `output/scratch-3-11/G/`.
Depends on: 3-07, 3-08, 3-11 (state of the art: tip `9269ebb`; new disc `output/scratch-3-11/G_new/ALLDATA.KWI`, sha 013586b5…; K1 classify output `output/scratch-3-11/classify_new`, extended dump `output/scratch-3-11/dump_new_ext`).
Runs alongside: nothing heavy. Heavy runs under `flock output/.heavy.lock`, one at a time; cbuild/make ≤ -j4; K1/harness ≤ -j6; never two heavy jobs; no cache drops; never wait with `pgrep` self-matching loops (wait on a file-based EXIT marker).
Tier: Sol (`codex exec -m gpt-6.1-sol -c model_reasoning_effort=high`), RE-risky. Mandatory Sonnet 5.5 review of the result (the reviewer re-runs the witness on its own sample).
Budget: no read cap. Work in checkpoints; at each checkpoint write the state to `output/scratch-3-12/handoff.md` (so a fresh worker can resume). Stop only on (a) PARTITION honestly closes or (b) every remaining row group has a documented, tested hypothesis that failed, with the next untested predicate named.

## The problem

Current unattributed after 3-07/3-08/3-11 (counts on the new disc): `background_boundary` about 14.6 M (+474 newly decoded by 3-11), `background` 517,785, plus small kinds 191. Do NOT accept this as spool. `docs/plans/04-c-core-orchestration/triage/causes_bg.md` and `review_3-07.md` hold what is established; read them first, with `DESIGN.md` Phase 3 contract, the cause class definitions in `briefs/3-07-cause-table-background.md`, the 3-05 rule schema (inlined there), and `triage/rules_bg.json`/`rules_other.json`.

## Facts already established (do not re-derive; cite)

- 88.47 % of the 18 M failing rows have a SENTINEL source (no same-type outline within `K1_DIAG_SAME` = 64 raw). The sampled sentinel boundary groups are 100 % invalid under the K1 witness (no same-type outline within 0.500001 raw) and ~90 % are farther than 64 raw from ANY outline of any type; in_eo_any = 1 for ~9 M type-291 L0 rows (the vertex lies inside a shape of another type) while in_eo_same = 0.
- Sentinel rows by (kind, level, type): boundary L0 291 11,127,845; L0 288 2,956,051; L0 289 394,514; L0 578 376,132; L2 289 109,364; L6 288 3,725; background L0 288/289/291/578 and L2 289 (the rest of the residual).
- All 31,416 `onb=0` boundary rows are on a leaf boundary whose internal sub-cell edges sit at frame 1024/2048/3072 (`_k1_bg.c k1_diag_fill` ~L567 compares only 0/4096).
- Partial mechanisms so far: R01 (checker, `background` fills valid even-odd inside) and S02 (spool, 1,939,053 rows, identified defective source rings) — keep them; do not widen S02 by similarity.

## Required approach (measurement first; each hypothesis gets tested, how, outcome, rows)

1. Characterize the residual rows in dump columns only (cheap, memmap): for sentinel `background_boundary` groups per (level, type): vertex position relative to the leaf frame (on a frame/leaf edge? interior? at which coordinate), piece vertex count, distance to the nearest same-type OUTLINE and to ANY outline, source-shape size, whether the vertex coordinates are rounding artifacts of a clip (frame-aligned, 1024-multiples), and whether pieces are SYNTHETIC (no spool shape owns them). Output distributions with counts; group by the predicate that best separates, not by a threshold picked to hit a count.
2. Hypotheses to test with witnesses/counterfactuals (not assumed true): (H8) the build emits synthetic complement/cover pieces (fills that tile what no spool shape covers, or sea/land balancing) whose boundary is a clip edge, not a spool outline — K1's boundary rule is then WRONG for them (checker), or the build is wrong to emit them (build); (H9) vertices created by cell/leaf clipping that K1's tolerance window mishandles beyond the `onb` case; (H10) type remap or merge between spool type codes and disc codes beyond what `any_type` showed; (H11) a shape that reaches the cell from outside the K1 shape window (H1 from 3-07, test on the sentinel groups); (H12) any hypothesis your column study suggests. For each: write the predicate as rules over dump or side-table columns (extend the side table with new u8/f32 columns the way `extend_dump_attempt3.py` did; document in `docs/provenance.md`).
3. Cause classification stays the fixed three: `checker` (witness: brute-force says the disc item is valid under the 3C-04 rule as written), `build` (disc differs from the build's own rule; counterfactual with a windowed rebuild, serial, -j4), `spool` (the faithful build of a defective spool shape; counterfactual removes the shape). A group is attributed only on a tested witness or counterfactual; if a mechanism explains more rows by construction (e.g. a synthetic-cover rule), state the predicate AND validate it on a random sample of at least 200 groups per stratum with the same witness, independently of the predicate.
4. A threshold in a rule needs a measurement story (the measured gap between populations); do not tune it to a count. A tolerance loosened to reduce a count is not a cause.
5. If a mechanism is `build` (the disc differs from the build's rule or the build emits something it should not): write it as a fix proposal for the orchestrator (location file:function, rows it must move to 0, the witness), do NOT edit code. If `checker`: say which K1 rule/window/tolerance and what the Python oracle `parser/tools/quantisation_roundtrip.py` does at that point (lockstep fix needed).
6. Re-run `k1_triage.py classify` (heavy, under lock) with the updated rules file against the extended dump; report the partition: per rule counts and the unattributed remainder per (kind, level, type). Cite Flash/K1 wall times only if you ran K1.

## Done evidence

`triage/causes_residual.md` + updated `triage/rules_bg.json`; classify output shows the new counts per cause class (checker | build | spool | unattributed) per kind; every new rule has witness or counterfactual output paths under `output/scratch-3-12/`; hypotheses H8-H12 each recorded (tested, how, outcome, rows); `docs/provenance.md` entries for any new side tables; `output/scratch-3-12/handoff.md` current.

## Report back

Under 600 tokens: status (`done` | `done with concerns` | `blocked` | `over budget`), counts moved per class (before/after, per kind), the mechanisms found with rows, what remains unattributed and the next predicate, deviations. Never resolve a contradiction silently. Do not spawn agents unless you must; do not edit code; do not start Phase 4; no `Workflow-Phase` trailer.
