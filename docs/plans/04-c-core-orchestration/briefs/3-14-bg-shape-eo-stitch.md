# Brief: 3-14 — Fix S02–S05 build: even-odd-aware closed-ring stitch in `bg_shape`

Consumer: the orchestrator (records the re-oracle, requests Sonnet 5.5 review of the diff + differing-cell list) and Cody (signs the re-oracle at phase close).
Owned paths: `parser/kiwiw/_cenc.c` (`bg_shape` / chain stitch / `emit_piece` call sites only — not unrelated encoders), any minimal `_e2.c` share required so `_bg_sub_cells` probes use the same corrected `kw__bg_shape`, matching tests under `parser/tests/`, `output/scratch-3-14/` (git-ignored). **Never overwrite** `output/scratch-3-11/G/ALLDATA.KWI` or `G_new/` (old oracles).
Commits: code + tests + unit record + `docs/provenance.md` for new scratch only. Never stage discs/dumps. Land `triage/rules_bg.json` S02–S05 cause=`build` notes only if not already on master from the 3-13 honesty packet.
Depends on: 3-13 ACCEPT-WITH-CONDITIONS (`triage/causes_rootcause.md`, `triage/review_3-13.md`); honesty status on master; dump/side tables under `output/scratch-3-12/` and `output/scratch-3-13/` as read-only evidence.
Runs alongside: nothing. Serial (touches `parser/kiwiw/`). Heavy under `flock output/.heavy.lock`; cbuild/make ≤ `-j4`; K1/harness ≤ `-j6`; no cache drops; free RAM tight — prefer **windowed** builds first; no second full-disc dump unless needed for classify.
Tier: Sol or Codex high (RE-risky). Mandatory Sonnet 5.5 review of the diff **and** the differing-cell list before treating as landed.
Budget: edit+tests ≤ 80 tool turns; each heavy step is one flock command. If a full-AU build/K1 is ≥ ~10 min, kick off here and verify with a follow-on unit (or report `done with concerns` + EXIT markers).

## Cited facts (copy from 3-13; do not re-derive)

- Rules **S02, S03, S04, S05** in `triage/rules_bg.json`: cause **`build`** (Sonnet ACCEPT-WITH-CONDITIONS). Target rows → 0: **17,058,955** = 517,648 fill + 16,541,304 boundary + 3 cover (S05). IDs/predicates/order unchanged; only cause/note flipped in 3-13.
- Mechanism (hypothesis for *how*; wrong-output is proven): `_cenc.c:bg_shape` (~L608–711) orients the whole ring by total signed area, stitches clipped chains via greedy counterclockwise successor (`g_sin`/`g_sout`) without per-chain even-odd filled-side classification or coincident-edge cancel; used-successor break + `emit_piece` can close with an interior chord → complements / leaf-edge connectors far outside producer bboxes.
- Exact-clip oracle + region-preserving complete-repair CFs (9 windows, 52 P rings): target fill/boundary residuals clear when the source region is expressed as simple faces **keeping the closing chord** — deleting the chord is unnecessary. Spool-pin **superseded**.
- Sonnet caveats in force: robust evidence = failing vertex + outline distance (not “every witness”); “5905” = vertex tests; R01 exclusivity unproven; CF = stratified sample; near-tail group-level; `clip_right_inside` **not** a rule predicate.
- Remainder **9,064** unattributed + PARTITION FAIL stay honest; do not pin them. Do not change K1 tolerances. Do not “fix” R01 in this unit.

## The change

Replace the closed-ring chain stitching in `_cenc.c:bg_shape` (and any shared chain helper it calls) with an **even-odd-aware arrangement / clip traversal**: classify each clipped chain’s local filled side under the same OR-of-per-ring even-odd contract as K1/`Region.inside`; cancel coincident edges with the same interior on both sides; traverse faces without inventing interior chords; pass correct faces through existing `emit_piece` densify/round. Division probes in `_e2.c:_bg_sub_cells` that call `kw__bg_shape` must share the correction.

**Non-goals:** extractor/spool edits; K1/Python tolerance changes; fixing R01/O01–O06; encoding `clip_right_inside` as a classify rule; full exhaustive repair of all ~71k P rings in this unit’s proof (window + classify targets suffice).

## Pre-edit checks (any fail → `blocked`)

C1. Capture OLD oracles: full-AU sha in force (G_new `013586b5…` / or HEAD build sha — record which), Perth `da13a775…`, keep discs.
C2. Confirm nine 3-13 CF windows’ original builds still byte-match G_new (or re-state if oracle moved); list windows from `causes_rootcause.md`.
C3. Goldens: name which `output/goldens-3C/` / committed goldens intersect self-crossing / wrap-risk cells; expect re-capture only for affected.
C4. Baseline classify on current dump+rules: quote S02–S05 row counts and the 9,064 unattributed (must match 3-13 partition arithmetic).

## Steps (in order)

1. **Synthetic / fixture tests first** (no heavy): construct self-crossing class-2 rings (bowtie, multi-lobe, chord-closed) whose lattice EO region is known; assert `bg_shape`/`enc_bg` output polygons equal the EO face union within frame (vertex+outline criteria per Sonnet), and that non-crossing rings stay byte-identical to HEAD on a fixed fixture set.
2. **Windowed proof (heavy, serial):** for each of the nine 3-13 windows, rebuild with the fix against **original** spool; require target fill/boundary (and S05 cover) residuals → 0 on original-spool K1 as in `causes_rootcause.md` tables; original (unfixed) window still matches G_new byte gate. Record per-window before/after.
3. **Full-AU re-oracle (Assumption 1):** build full-AU + Perth under lock. Cell-by-cell compare old vs new: differing cells must be **explained** (list path + counts per level). Any unexplained extra cell → `blocked`. Perth: unchanged unless a predicted cell moves — then record new sha + exact cells.
4. **Classify gate:** dump (or reuse extended dump if still valid against new disc — if invalid, new dump under lock) + `k1_triage.py classify`: S02/S03/S04/S05 rows → **0**; other rules unchanged except deltas you explain by cause (R01 may move — **disclose**, do not silently absorb into build credit; if R01 drops, record counts and leave R01 cause as checker with the 3-13 caveat unless a separate unit reclassifies). Unattributed must not be force-pinned; 9,064 may shrink only with named new rules (out of scope) or stay.
5. **Gates:** `-j1` == `-j12` on a window or full build as practical; H-budget tests; assembly under ~1 min or name regression cause; pytest relevant + full `parser/tests` as feasible under lock scheduling.
6. **Record** in `IMPLEMENTATION.md` (3-14 heading): C1–C4, old/new shas, differing-cell TSV path, per-window tables, per-rule before/after, Sonnet review pending note. Provenance for scratch-3-14.

## Done evidence

- Synthetic tests green; nine windows clear target residuals; full-AU differing cells listed and justified; classify shows S02–S05 = 0; Sonnet 5.5 review of diff + cell list requested (orchestrator seats — Design/CHM).
- No spool pin; no tolerance loosen; no live `extend.py` semantics change beyond the C stitch.

## Report back

Under 600 tokens: status (`done` | `done with concerns` | `blocked` | `over budget`), old/new shas, differing-cell count, S02–S05 before→after, R01 delta if any, deviations. Never resolve a contradiction silently. Do not start Phase 4; no `Workflow-Phase` trailer.
