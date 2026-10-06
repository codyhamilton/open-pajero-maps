# Encoder content trim vs R parity (R-G9-3) — proven cause with named children

Plan 42 closed in two phases with a **proven cause**. There is no encoder
change, and the oracle in force stays `4e6b0de7`. All trimming on the
oracle is the `dv_shrink` tier, in two sub-cells.

- **L0 (1755,591)(2,1):** R lacks the 227 dropped type-288 backgrounds
  (type census: R has 0 type-288 in the parent).
  - The 207 roads are cut to 0 by the shrink fallback (fixed kind order
    road → background → name), under a frame overflowing with type-288
    content R does not have.
  - R has 3,695 raw of road there, so the road loss is a **real deviation
    by volume**; per-item identity is not decidable. Child R-G9-3-a.
- **L8 (7,4)(3,0):** the 308 dropped pieces are 2-vertex stubs. 295 are
  sub-quantum, all lie within 0.768 raw of kept roads (R step 1 raw), and
  they are 2.0% of length.
  - No geometry is lost at R's resolution. The count reflects **G
    fragmentation** (R-G9-3-b).
  - The first-pass "priority difference" verdict was withdrawn after the
    review (FAIL → rework → PASS_WITH_FOLLOWUPS).
- **Named children (open, maps-parity-carried):**
  - R-G9-3-a: L0 road loss;
  - R-G9-3-b: L8 fragmentation;
  - R-G9-3-c: L8 under-selection against R (dc 10 missing);
  - R-G9-3-d: 5 degenerate G L0 links at the parent's east edge.
- **Witness:** kept at
  `docs/plans/04-c-core-orchestration/triage/trim_r_parity/`.
- **Reviews:** a Claude CLI clean-context seat (disclosed; Codex is
  weekly-limited).

Plan 04 Phase 3 is **not** claimed closed.

## Intent
User request, verbatim (DESIGN):
> Cody's standing rule (2026-10-05, hard): Maps is complete only when end-to-end generation matches the original DVD in every aspect that can be verified, every claim, assumption, and implementation aspect is verified and proven, and there are no unexplained deviations — each has a root cause.

Close Design-owned residual row R-G9-3: encoder content trim on the oracle in force, with no R-parity proof and invisible to K1. Outcome: expand-to-zero with a confined, recorded successor oracle, or a proven cause (including proven non-deviation if R drops exactly the same items). Never a relabel. Oracle `4e6b0de7…` or later. Heavy work only under flock plus the wrapper (encode ≤ `-j4`, K1 ≤ `-j6`). Master direct. No plan 04 Phases 4–6. Do not run the 3-90 brief.

## Why This Existed
The encoder trims items by priority when a divided sub-cell cannot fit the 131,070 B frame ceiling (`_e2.c` `dv_trim`, "last tier"). It prints `** >1% BLOCKER **` when a level's dropped share exceeds 1% (`parser/build_alldata.py` ~L645–652).

**Ground (master `b10e787`; manifest of `4e6b0de7` read-only on host):**

| Level | Kind | Dropped / total | Sub-cells | Note |
| --- | --- | --- | --- | --- |
| 8 | road | 308 / 14,012 (2.198%) | 1 (hard-ceiling fallback sub-cell (3,0), 308 / 2,417) | prints BLOCKER; identical on `87a01b14`, `013586b5`, `4ed9cd80`, `4e6b0de7` (3-14 TRIM ruling) |
| 0 | road | 207 / 3,015,057 | 1 | same absolutes as the `l0_divided_trim_halo` golden window (1755,591)–(1756,592) |
| 0 | background | 227 / 11,029,580 | 1 | same window |

- **Sources:** `output/scratch-34/G_new/manifest.json` `trimmed_items`; plan 35 `run_p1.log` L134, L152–153; plan 04 IMPLEMENTATION L230–233 (Design TRIM ruling 2026-10-03: "known budget … Design ticket for any expand-to-zero follow-up").
- **No R-parity measurement exists** for these items. K1 checks G against the spool only for emitted items, so trimmed items are invisible to it. The manifest gives counts only, not item identity or parent cell (except via the window golden and the build log).

R is the reference. If R carries the trimmed items in those parcels (for example, deeper division or a different sub-cell split), our trim is a deviation. If R carries none of them, or exactly the same subset, that is evidence for a shared budget rule.

## What Landed

Master direct; no `parser/` change.
- **Phase 1:**
  - The instrumented item dump (throwaway worktree, byte-equal frames) and
    the R decode.
  - The first verdict FAILED review. It was reworked with a calibrated
    control, volume, census and stub analysis, then re-reviewed
    PASS_WITH_FOLLOWUPS, and N1–N9 were applied.
- **Phase 2:** proven-cause disposition; R-G9-3 discharged with children
  a–d; OVERVIEW updated. The re-review recommended this exact close.
- **Close-out:** the witness and reviews moved to
  `triage/trim_r_parity/`. The witness was re-run at the new path with an
  unchanged JSON.

Master direct. Oracle in force: `4e6b0de7…`.

## Phase 1 — trimmed items identified and checked against R

### Item identity (Contract 1)

The trimmed items were dumped by a bounded instrumentation hook in a
**throwaway worktree** at `20b4bf9`. The hook is in
`triage/trim_r_parity/instr_e2.patch` and is not landed. It writes to
`KW_TRIM_DUMP=<path>` from both trim tiers in `_e2.c`: `dv_trim` (tag
`trim`) and `dv_shrink` (tag `shrink`).

- **Contents:** every item of a trimmed kind in the trimmed sub-cell, in
  priority order, kept (K) or dropped (D). Each row carries: level, parent,
  sub-cell, kind, rank, item id, parent-record index, and the geometry. Roads
  carry `dc=<display class>|lat,lon;…` for the chain piece. Backgrounds carry
  `tc=<type>|lat,lon;…` for the parent-record ring, which includes shapes
  shared in by the overlap pass.
- **Output unchanged:** the instrumented and plain builds produce byte-equal
  `--frame-dump` bins and TSVs for both runs below.
- **Count gate:** the **dropped** counts equal the full-AU absolutes on
  `4e6b0de7` (its manifest `trimmed_items`: 207 / 227 / 308).
  - The window totals (1,083 roads / 8,824 backgrounds) are window-only, not
    the full-AU totals (3,015,057 / 11,029,580).
  - Stronger check (review F7): all 16 L0 (1755,591) frames and all 6 L8
    (7,4) frames of the window builds occur byte-identical inside the oracle
    `ALLDATA.KWI`. The window builds therefore reproduce the oracle's
    trimmed item set.
- **Item key (review F6):** `item` / `par` are row indices into the level's
  E2 input table, which is built from the spool. `(level, kind, row)` is
  therefore a stable spool key.
  - For backgrounds `par == item`. A shape shared in by the overlap pass
    keeps its source row, but its source cell is not recorded in the dump.
  - **Not captured:** the `dv_key` priority fields and the encoded bytes per
    item; the dump has the rank only. This is a limit; no verdict below
    depends on these fields.

| run | command | trim lines (dropped counts: instrumented = plain = full-AU absolutes; window totals are window-only) |
|---|---|---|
| L0 window | `--window 0 1755 591 1756 592 -j 1` | road 207/1,083 in 1 sub-cell; background 227/8,824 in 1 sub-cell |
| L8 level | `--levels 8 -j 1` | road 308/14,012 in 1 sub-cell |

- **Dumps:** `triage/trim_r_parity/trim_l0_1755_591.tsv.gz` (6,849 rows) and
  `triage/trim_r_parity/trim_l8_7_4.tsv.gz` (2,417 rows).
- **Where trimming happens:** all trimming is in the `shrink` tier (the
  whole sub-cell is over the 131,070 B ceiling). The `trim` tier fired 0
  times.
- **Shrink mechanism (review F8):** `dv_shrink` first binary-searches each
  kind against its per-kind limit, in `dv_order`.
  - If the frame still does not fit, a fallback loop cuts kinds in the
    **fixed order road → background → name** until it fits.
  - At L0 (2,1) the fallback takes roads to 0. The 227 backgrounds are cut
    by the per-kind pass or by the fallback; which one is not shown.
  - This kind order is a separate policy from `dv_order`. Any priority
    change has to account for it.
- **L0 parent (1755,591):** Melbourne, near Tullamarine (lat −37.6875 …
  −37.6667, lon 144.844 … 144.875).
  - Sub-cell (2,1) of the 4 × 4 division drops **all 207** road pieces
    (ranks 0–206; 0 kept).
  - It drops the lowest-priority **227 of 6,642** backgrounds, all type 288
    (ranks 6,415–6,641).
  - Its frame is 131,064 B.
- **L8 parent (7,4):** SE Queensland (lat −28.67 … −23.33, lon 146 … 154).
  - Sub-cell (3,0) drops the lowest-priority **308 of 2,417** road pieces
    (ranks 2,109–2,416), all display class 12.
  - Its frame is 131,056 B.

### R decode (Contract 2) and G control (Contract 3)

`triage/trim_r_parity/trim_witness.py` does bounded R leaf preads and bounded leaf
decodes of the oracle `4e6b0de7` (G, read only). It writes
`triage/trim_r_parity/trim_witness.json`.

| parent | R topology | G topology |
|---|---|---|
| L0 (1755,591) | **undivided**, 1 leaf `[507]`, 23,680 B: 179 road links, 21 background records | 4 × 4 division, 16 frames, 310,268 B: 1,108 kept road pieces, 8,945 background items (8,777 of them type 288) |
| L8 (7,4) | **2 × 2**, leaves `[19,0..3]` = 6,176 / 106,400 / 12,448 / 31,104 B, with 30 / 750 / 25 / 124 links | 4 × 4, 6 non-empty frames; 2,979 kept road pieces; sub (3,0) held 2,417 before the trim |

- **Leaf rects (review F5, fixed):** a divided leaf's rect is now its
  quadrant (2 × 2) or sixteenth (4 × 4), derived from the leaf index.
  - It was checked against the decoded data. R data and G backgrounds fall
    0.0 raw outside their rects.
  - G L0 road pieces are clipped to their sub-cells, with one exception.
    **5 degenerate links** in western sub-cells (leaves 0, 4, 4, 4 and 8;
    6–10 vertices, dc 12/2/7/7/7) have every vertex at one point, x = 4096,
    the parent's east edge.
    - They are the only data outside a rect, by up to 3,072 raw.
    - Whether they are a D1 decode artefact or an encoder defect in the
      oracle is **not determined**. This is a named residual (R-G9-3-d).
    - Their effect on the control is 5 of 1,108 pieces.
  - G volumes count length inside each leaf's rect.
- **R quantum:** every R leaf here has frame range 4096 over the whole
  parent, so one R coordinate step is **1 parent raw unit**. That is
  0.56 × 0.73 m at L0 and about 145 × 188 m at L8.

#### The v1 rule is superseded (review F1–F3)

The first rule was: every vertex within 1 parent-raw unit of a same-class R
polyline, plus a type-gated ring rule for backgrounds. It is kept in the
script and the JSON (`rule_v1_not_validated`, per-item `status`), but **it
drives no verdict**.

- At L0, one unit is below the OSM ↔ vendor offset: the control median is
  31 raw.
- At L8, one unit is R's quantum, so "present" meant "near an R road", not
  "R carries this item".
- The class code is not a G ↔ R identity: R has no dc 2 at L0, and has dc 10
  plus dc 12 at L8, where G has only dc 12.

**Corrected numbers (v2):**

| level / kind | dropped | evidence (v2, any class) |
|---|---|---|
| L0 road | 207 (all) | see "L0 roads" below |
| L0 background | 227 (type 288) | type census |
| L8 road | 308 | piece length plus redundancy against kept pieces |

#### L0 roads (control calibrated; review F2)

- **Control:** 1,108 kept G road pieces in the parent's other 15 sub-cells.
  The trimmed sub-cell has no kept road.
  - Metric: the per-piece median of the sampled distance to the nearest R
    road of any class.
  - Control quantiles: q10 / q50 / q90 = 2.2 / 31.1 / 228.0 raw.
  - Control recall: 3.6% at 1 raw, 40% at 20, 76% at 100, 88% at 200 and
    98.9% at 500.
  - The tolerance with 90% recall is **500 raw**, about half the sub-cell
    width, so **per-item R presence is not decidable at L0**. The OSM and
    vendor geometries differ by tens of metres.
- **Dropped 207:** q10 / q50 / q90 = 15.7 / 100.6 / 266.3 raw.
  - The distances are farther than the control: 50% within 100 raw against
    76%, and 26% within 50 against 59%.
  - 164 of the 207 are dc 2. Class code is not a G ↔ R identity, so the
    geometric per-class control is the evidence (re-review N3).
    - Kept-piece q50 distance to any R road: dc 2 63.8 / dc 4 3.2 / dc 7
      6.1 / dc 9 7.2 / dc 10 143.5 / dc 12 3.4 raw.
    - Dropped dc 2 q50: 126.8 raw.
    - Within 20 raw: 25% of kept dc 2 and 1% of dropped dc 2.
    - **G's dc 2 is geometrically distant from R across the parent, kept and
      dropped alike.** That is an upstream L0 selection matter, not a trim
      matter.
    - The other 43 dropped pieces are closer to R. Within 20 raw: dc 12
      38%, dc 4 56%, dc 7 30% and dc 9 75%. These are the likely
      R-carried part, consistent with R's 3,695 raw in (2,1).
    - Per-class numbers are in `v2.road_control_by_class`.
- **Volume** (length inside each G sub-cell rect, raw units):
  - Sub-cell (2,1): **G emits 0 after the trim; R has 3,695 raw** (about
    2.3 km). G pieces kept in all leaves have 19 raw of spill-in inside the
    (2,1) rect.
  - G before the trim had 37,039 raw there, a G/R ratio of 10.0.
  - The other 15 sub-cells have G/R ratios of 0.79–12.7 (median 2.6). G is
    denser than R across the parent, and (2,1) is at the dense end.

#### L0 backgrounds (type census; review F2)

- R's whole leaf has **0 type-288 records**. Its class-2 types are 1024 ×19
  and 321 ×1, plus class-1 291 ×1.
- G's parent has 8,777 type-288 items. All 227 dropped items are type 288,
  and all 6,628 pre-trim type-288 items in (2,1) are absent from R by type.
- The geometric ring rule was never exercised, because of the type gate. The
  evidence is the census, not geometry. No positive control for the ring
  rule was built; that is a limit.

#### L8 roads (review F1, F3)

- **Shape:** all 308 dropped pieces are **2-vertex stubs**.
  - Length q10 / q50 / q90 / max = 0.06 / 0.17 / 0.65 / 4.69 raw. The kept
    pieces' median is 1.15 raw.
  - The total dropped length is **94 raw**, 2.0% of the sub-cell's
    pre-trim 4,738 raw.
- **Redundancy:** this evidence carries the L8 verdict (re-review N4).
  - The **maximum sampled distance** from any dropped stub to a kept G
    piece is **0.768 raw** (step 0.02), under one R step.
  - The 308 dropped pieces form **237 connected components**, the largest
    5.5 raw long. No run of dropped stubs therefore opens a gap of one R
    step.
  - Each dropped piece is its own spool record: 308 distinct `par`, 0
    shared with kept pieces. 294 share an endpoint with a kept piece.
  - Priority correlates with length: Spearman rank–length is −0.796.
  - By category, 295 are sub-quantum (shorter than 1 R step) and 13 are
    redundant. Given the shared endpoints, these categories are
    near-tautological, and the R-specific test was **not exercised**
    (0 pieces reached it).
  - G also **keeps 968 equally sub-quantum pieces**, which supports
    "fragmentation".
- **Control** (kept 2,109, any class): recall is 56% at 1 raw and 92% at
  10. The dropped stubs' distances match it: 57% at 1 raw and 94% at 10.
  - The v1 rule, any class: 1,053 kept present / 815 absent / 241
    ambiguous. Same class: 752 / 1,162 / 195.
- **Volume:**
  - Decoded against decoded: R's road length inside sub (3,0) is 6,623 raw
    and G's kept is 5,373. Exact dump geometry gives G's kept 4,645 and
    pre-trim 4,738. Decode quantisation of tiny pieces inflates G by about
    16%. **G is not above R by length** either way.
  - In the parent's other G leaves, **G under-selects against R**
    (re-review N1). Leaf 2 has 225 against 4,786 raw; leaves 11 and 14 have
    0 against 1,251 and 3,336.
    - R has 801 dc 10 links in the parent; G has no dc 10 (2,979 dc 12).
    - This is a named residual (R-G9-3-c).
  - G does over-fragment: 2,979 pieces in the parent against R's 929 links,
    and 2,417 pieces in (3,0) against 750 links in R's whole quadrant.

### Verdict (Contract 4; revised after review)

- **L0 roads: the deviation is real by volume; per-item identity is not
  decidable.**
  - Sub-cell (2,1) is drawn with 0 roads where R has 3,695 raw of road.
  - The dropped pieces are farther from R than the control (q50 100.6
    against 31.1 raw). Dropped dc 2 is distant from R, like kept dc 2
    parent-wide. The geometry cannot say which individual pieces R
    carries.
  - Mechanism, from the code and the dump: the frame overflows with 6,628
    type-288 items, a type R lacks in the whole parent.
    - Roads are cut to 0 by the shrink fallback, which cuts roads first.
    - The 227 backgrounds were cut either by the per-kind pass (every
      per-kind limit is the 131,070 B ceiling) or by the fallback. Which one
      is not shown (re-review N6).
- **L0 backgrounds: `R-lacks-trimmed` by type census.** R has 0 type-288
  records in the parent. The trim removes content R does not have.
- **L8 roads: not a priority difference.** The earlier "priority difference
  is the named cause" is **withdrawn** (review F4).
  - The dropped items are sub-quantum or redundant stubs, totalling 2% of
    length, all within one R step of kept G roads.
  - At R's resolution the trim removes no distinguishable geometry. The
    count-based "2.198% > 1% BLOCKER" line counts fragments.
  - The trimmed count comes from **G fragmentation**: 2,979 pieces against
    R's 929 links per parent. The pieces are separate short spool records
    that touch kept roads. The cause of the short records is not
    established (R-G9-3-b).
  - Hypotheses after review:
    - (a) sub-quantum stubs: **supported**;
    - (b) G selection relative to R: G **under**-selects across the parent
      (dc 10 missing; R-G9-3-c). If G selected what R selects, (3,0) would
      hold more road bytes, so fragmentation is a partial account of the
      trim pressure;
    - (c) priority: **not needed** to explain the drop.
- **R topology difference:**
  - L8: R divides (7,4) 2 × 2, and its largest quadrant is 106,400 B with
    750 links. We divide 4 × 4, and one sixteenth held 2,417 pieces.
  - L0: R does not divide (1755,591); we divide it 4 × 4.
- **For Phase 2:** no R-evidenced trim-priority rule exists.
  - The L0 loss comes upstream, from type-288 over-emission (R-G9-3-a)
    through the fixed shrink kind order.
  - The L8 count comes from fragmentation (R-G9-3-b).
- **`leaf_rects` grid inference** is a heuristic (2 × 2 when every index is
  below 4). It now asserts 0.0 background outside-distance on every use
  (re-review N7).
- **Clamp wording** (re-review N9): only out-of-reach values are set to 600.
  In-reach values are exact.

### Phase 1 review

Claude CLI clean-context seat (disclosed; Codex is weekly-limited):
**FAIL** on P1.3 / P1.4 / C3. The text is kept as `triage/trim_r_parity/reviews/p1-REVIEW.md`.
Fixes:

- **F1:** the L8 rule now uses piece length, redundancy against kept pieces
  and R-specific evidence. The 144 "R-has" result is withdrawn.
- **F2:** L0 roads have a calibrated control and are declared not decidable
  per item, with volume evidence. L0 backgrounds rest on the type census.
- **F3:** any-class is primary, and class agreement is reported separately.
- **F4:** the L8 verdict is restated with hypotheses; "priority" is
  withdrawn.
- **F5:** the quadrant / sixteenth leaf rects are fixed and data-checked.
- **F6:** the item key is stated; the `dv_key` fields and per-item bytes are
  a stated limit.
- **F7:** the count wording is fixed, and oracle byte-identity is recorded.
- **F8:** the shrink kind order is stated.

### Phase 1 re-review

Claude CLI clean-context seat (disclosed): **PASS_WITH_FOLLOWUPS**. F1–F8
are resolved; F8 mostly, with N6 now fixed. The text is kept as
`triage/trim_r_parity/reviews/p1b-REVIEW.md`. New findings N1–N9 are applied:

- **N1:** G under-selection at L8 is recorded (R-G9-3-c), and hypothesis (b)
  is relabelled.
- **N2:** the 5 degenerate east-edge links are recorded, with no
  "not clipped" claim (R-G9-3-d).
- **N3:** a per-class geometric control replaces the dc-2 identity
  argument.
- **N4:** max distance, components, record distinctness, Spearman and the
  968 kept sub-quantum pieces are recorded in the JSON and the text.
- **N5:** volumes are compared like for like, with the inflation stated.
- **N6:** the stage that cut the 227 backgrounds is stated as not shown.
- **N7:** the grid assertion is added.
- **N8:** follow-ons are named, as rows R-G9-3-a..d (Phase 2).
- **N9:** the clamp wording is fixed.

The witness was re-run after the fixes.

## Phase 2 — proven cause (no expand-to-zero)

- **Outcome branch:** `proven-cause`, per the DESIGN Phase 2 outcome. There
  is no fix and no encoder change, so no successor oracle; the oracle in
  force stays `4e6b0de7`. Nothing changed in `parser/`.
- **Why not expand-to-zero:**
  - Trimmed totals reach 0 only by raising the frame ceiling (DESIGN
    rejects this) or by changing what is cut. Phase 1 shows that no
    R-evidenced trim-priority rule exists.
  - **L0:** what overflows the frame is type-288 content R does not carry.
    Cutting backgrounds before roads would restore roads at L0. At L8 the
    same kind-order change would cut backgrounds first in (3,0), where R
    carries many class-2 records, so that rule is not R-evidenced across
    the affected cells.
  - The real L0 fix is upstream (type-288 emission). That is outside this
    plan's surfaces (`_e2.c` division/trim tier, R-evidenced only).
  - **L8:** the dropped stubs are below R's resolution. The count reflects
    fragmentation, not lost geometry.
- **Per level and kind:**

  | level / kind | dropped | disposition |
  |---|---|---|
  | L0 background | 227 (type 288) | R-lacks-trimmed, by type census: R has 0 type-288 in the parent |
  | L0 road | 207 (all) | proven cause: shrink fallback kind order under type-288 overflow. The deviation is real by volume (R 3,695 raw vs G 0); per-item identity is not decidable. Child **R-G9-3-a** |
  | L8 road | 308 | proven cause: G fragmentation. All dropped stubs are within 0.768 raw of kept roads (R step 1 raw), 2.0% of length. Child **R-G9-3-b** |

- **`residuals.tsv`:**
  - R-G9-3 is discharged by plan 42 Phase 2, as a proven cause with named
    children.
  - The children are R-G9-3-a (L0 roads), R-G9-3-b (L8 fragmentation),
    R-G9-3-c (L8 under-selection) and R-G9-3-d (5 degenerate L0 links).
  - All four are open, `maps-parity-carried`; Design may promote them.
- **OVERVIEW:** the residual list now names plan 42 and the children.
- **Witness:** at close it moves to
  `docs/plans/04-c-core-orchestration/triage/trim_r_parity/`.

## Commits

- `e4d2dca` — P1 witness (`:1`).
- `ca85ede` — P1 rework after the FAIL review (`:1`).
- `d0a3b5c` — P1 re-review follow-ups (`:1`).
- `fbed5c3` — P2 proven cause, residuals and OVERVIEW (`:2`).
- Close-out (`:done`).

## Not done

- No expand-to-zero. It would need either the rejected ceiling raise or a
  cut rule R does not evidence.
- Upstream items stay with Design as R-G9-3-a..d:
  - type-288 over-emission;
  - the kind-order policy;
  - L8 fragmentation and under-selection;
  - the degenerate links.
- Per-item `dv_key` fields and bytes were not captured (stated limit).
- Codex confirmation waits for the Codex reset (2026-10-10 11:50 AEST).
